from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, flash
from flask_bcrypt import Bcrypt
import sqlite3
import os
from datetime import datetime, timedelta
from invoice_generator import generate_invoice

# Initialize Flask app and Bcrypt
app = Flask(__name__)
bcrypt = Bcrypt(app)

# Configure the Flask secret key for session management
app.config['SECRET_KEY'] = 'cabral13'  # Make sure to replace this with a strong secret key

# Directory for storing generated invoices
INVOICE_DIR = "invoices"
os.makedirs(INVOICE_DIR, exist_ok=True)

# Database connection
def get_db_connection():
    conn = sqlite3.connect('timesheet.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
def initialize_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create necessary tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            phone_number TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            total_hours REAL,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_number TEXT PRIMARY KEY,
            username TEXT,
            date TEXT,
            total_hours REAL,
            total_payment REAL,
            filename TEXT,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    conn.commit()
    conn.close()

initialize_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username').strip().lower().replace(" ", "")
    password = request.form.get('password')

    # Log the incoming username and password
    app.logger.info(f"Attempting login with username: {username}")

    try:
        # Create a connection to the database
        conn = get_db_connection()
        app.logger.info("Database connection established.")

        # Query the database for the user, logging the query
        query = "SELECT username, password, role FROM users WHERE LOWER(REPLACE(username, ' ', '')) = ?"
        app.logger.info(f"Executing query: {query} with username: {username}")
        
        user = conn.execute(query, (username,)).fetchone()

        # Check if user is found
        if user:
            app.logger.info(f"User found: {user['username']} - Role: {user['role']}")
        else:
            app.logger.warning(f"User not found: {username}")
        
        if user and bcrypt.check_password_hash(user['password'], password):
            # Successful login
            app.logger.info(f"Login successful for user: {username}")
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'employee':
                return redirect(url_for('employee_dashboard', username=username))
        
        app.logger.warning(f"Invalid credentials for user: {username}")
        return jsonify({'message': 'Invalid credentials'}), 401

    except Exception as e:
        # Catch all exceptions, log the error, and return an error message
        app.logger.error(f"Error during login process: {e}")
        return jsonify({'message': 'Internal Server Error'}), 500

    finally:
        # Ensure the database connection is closed
        if conn:
            conn.close()
            app.logger.info("Database connection closed.")

@app.route('/admin_dashboard')
def admin_dashboard():
    conn = get_db_connection()
    employees = conn.execute('SELECT * FROM users WHERE role = "employee"').fetchall()
    time_entries = conn.execute('SELECT * FROM time_entries').fetchall()
    invoices = conn.execute('SELECT * FROM invoices').fetchall()
    conn.close()

    return render_template('admin_dashboard.html', employees=employees, time_entries=time_entries, invoices=invoices)

@app.route('/add_employee', methods=['POST'])
def add_employee():
    name = request.form.get('name').strip().title()
    role = request.form.get('role')
    phone_number = request.form.get('phone_number')
    hashed_password = bcrypt.generate_password_hash('123').decode('utf-8')

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password, role, phone_number) VALUES (?, ?, ?, ?)', 
                     (name, hashed_password, role, phone_number))
        conn.commit()
    except sqlite3.IntegrityError:
        flash("User already exists!", 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        conn.close()
    flash("User added successfully!", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/employee_dashboard/<username>')
def employee_dashboard(username):
    conn = get_db_connection()
    try:
        # Fetch time entries and invoices
        entries = conn.execute('SELECT * FROM time_entries WHERE username = ?', (username,)).fetchall()
        invoices = conn.execute('SELECT * FROM invoices WHERE username = ?', (username,)).fetchall()
    except sqlite3.Error as e:
        app.logger.error(f"Database error: {e}")
        return "An error occurred while loading the dashboard.", 500
    finally:
        conn.close()

    return render_template('employee_dashboard.html', username=username, entries=entries, invoices=invoices)

@app.route('/add_time_entry', methods=['POST'])
def add_time_entry():
    username = request.form.get('username')
    date = request.form.get('date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    try:
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = datetime.strptime(end_time, "%H:%M")
        total_hours = (end_dt - start_dt - timedelta(minutes=30)).seconds / 3600.0
    except ValueError:
        flash("Invalid time format. Please enter valid start and end times.", 'danger')
        return redirect(url_for('employee_dashboard', username=username))

    conn = get_db_connection()
    conn.execute('INSERT INTO time_entries (username, date, start_time, end_time, total_hours) VALUES (?, ?, ?, ?, ?)', 
                 (username, date, start_time, end_time, total_hours))
    conn.commit()
    conn.close()
    flash("Time entry added successfully.", 'success')
    return redirect(url_for('employee_dashboard', username=username))

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice_route():
    username = request.form.get('username')
    conn = get_db_connection()
    entries = conn.execute('SELECT date, total_hours FROM time_entries WHERE username = ?', (username,)).fetchall()
    if not entries:
        return jsonify({'error': 'No time entries found for this user.'}), 404

    total_hours = sum(entry['total_hours'] for entry in entries)
    invoice_date = datetime.now().strftime("%Y-%m-%d")
    invoice_number = f"{invoice_date.replace('-', '')}_{username}"
    filepath = os.path.join(INVOICE_DIR, f"{invoice_number}.pdf")

    generate_invoice(invoice_number, username, {"Company Name": "GOAT Removals"}, entries, total_hours, filepath)

    conn.execute('INSERT OR IGNORE INTO invoices (invoice_number, username, date, total_hours, total_payment, filename) VALUES (?, ?, ?, ?, ?, ?)',
                 (invoice_number, username, invoice_date, total_hours, total_hours * 25, filepath))
    conn.commit()
    conn.close()

    return send_from_directory(INVOICE_DIR, os.path.basename(filepath), as_attachment=False)

@app.route('/send_invoice_to_db', methods=['POST'])
def send_invoice_to_db():
    username = request.form.get('username')
    conn = get_db_connection()
    invoice = conn.execute('SELECT * FROM invoices WHERE username = ? ORDER BY date DESC LIMIT 1', (username,)).fetchone()
    conn.close()

    if invoice:
        return jsonify({'message': 'Invoice sent successfully!'})
    return jsonify({'error': 'No invoice available to send!'}), 400

@app.route('/download_invoice/<filename>')
def download_invoice(filename):
    filepath = os.path.join(INVOICE_DIR, filename)
    if os.path.exists(filepath):
        return send_from_directory(INVOICE_DIR, filename)
    return jsonify({'error': 'Invoice not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
