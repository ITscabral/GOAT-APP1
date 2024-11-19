from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, send_from_directory, abort
import sqlite3
import os
from datetime import datetime, timedelta
from invoice_generator import generate_invoice
from db_handler import Database


app = Flask(__name__)

def ensure_invoice_directory():
    directory = "/tmp/invoices"
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        print(f"Invoice directory created: {directory}")
    else:
        print(f"Invoice directory already exists: {directory}")

# Call the function to ensure the directory exists
ensure_invoice_directory()


# Initialize the database and create tables if they don't exist
def initialize_db():
    # Define the persistent database path
    db_path = "/var/data/timesheet.db"

    # Ensure the directory for the database exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Connect to the database
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()

    # Create the users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            phone_number TEXT
        )
    ''')

    # Create the time_entries table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS time_entries (
            username TEXT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')

    # Create the invoices table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_number INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            date TEXT NOT NULL,
            total_hours REAL NOT NULL,
            total_payment REAL NOT NULL,
            filename TEXT NOT NULL,
            sent INTEGER DEFAULT 0,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    print(f"Database initialized at: {db_path}")

# Call the function to initialize the database
initialize_db()

def get_db_connection():
    # Ensure the persistent directory is correctly specified
    db_path = '/var/data/timesheet.db'

    # Check if the database file exists
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at {db_path}")

    # Connect to the SQLite database
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    try:
        username = request.form.get('username').strip().lower().replace(" ", "")
        password = request.form.get('password')

        if not username or not password:
            return jsonify({'message': 'Username and password are required'}), 400

        conn = get_db_connection()
        query = "SELECT role FROM users WHERE LOWER(REPLACE(username, ' ', '')) = ? AND password = ?"
        user = conn.execute(query, (username, password)).fetchone()
        conn.close()

        if user:
            role = user['role']
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'employee':
                return redirect(url_for('employee_dashboard', username=username))
        else:
            return jsonify({'message': 'Invalid credentials'}), 401

    except sqlite3.Error as e:
        return jsonify({'error': f"Database error during login: {e}"}), 500

@app.route('/admin_dashboard')
def admin_dashboard():
    conn = get_db_connection()
    teams = {
        "Team 1 - Jackson C & Lucas C": ["Jackson Carneiro", "Lucas Cabral"],
        "Team 2 - Bruno V & Thallys C": ["Bruno Vianello", "Thallys Carvalho"],
        "Team 3 - Michel S & Giulliano C": ["Michel Silva", "Giulliano Cabral"],
        "Team 4 - Pedro C & Caio H": ["Pedro Cadenas", "Caio Henrique"],
    }

    conn.row_factory = sqlite3.Row
    employees = conn.execute('SELECT * FROM users WHERE role = "employee"').fetchall()
    entries = conn.execute('SELECT * FROM time_entries').fetchall()
    invoices = conn.execute('SELECT * FROM invoices').fetchall()
    conn.close()

    employee_list = []
    for team_name, team_members in teams.items():
        for member in team_members:
            employee_data = next((emp for emp in employees if emp['username'].strip().title() == member), None)
            employee_list.append({
                'username': member,
                'team': team_name,
                'role': employee_data['role'] if employee_data else None
            })

    entry_list = []
    for entry in entries:
        entry_data = {
            'username': ' '.join(entry['username'].strip().title().split()),
            'date': entry['date'],
            'start_time': entry['start_time'],
            'end_time': entry['end_time'],
            'total_hours': round(
                (datetime.strptime(entry['end_time'], "%H:%M") - datetime.strptime(entry['start_time'], "%H:%M") - timedelta(minutes=30)).seconds / 3600.0, 2
            ),
            'team': next((team for team, members in teams.items() if entry['username'].strip().title() in members), None)
        }
        entry_list.append(entry_data)

    invoice_list = []
    for invoice in invoices:
        invoice_data = {
            'invoice_number': invoice['invoice_number'],
            'username': ' '.join(invoice['username'].strip().title().split()),
            'date': invoice['date'],
            'total_hours': invoice['total_hours'],
            'total_payment': invoice['total_payment'],
            'filename': invoice['filename']
        }
        invoice_list.append(invoice_data)

    return render_template('admin_dashboard.html', teams=teams.keys(), employees=employee_list, entries=entry_list, invoices=invoice_list)

@app.route('/add_employee', methods=['POST'])
def add_employee():
    name = request.form.get('name')
    role = request.form.get('role')
    phone_number = request.form.get('phone_number')

    if not all([name, role, phone_number]):
        return jsonify({'error': 'All fields are required!'}), 400

    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO users (username, password, role, phone_number) VALUES (?, ?, ?, ?)',
            (name.lower().replace(" ", "_"), '123', role, phone_number)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    except sqlite3.IntegrityError:
        return jsonify({'error': 'User already exists!'}), 400

@app.route('/employee_dashboard/<username>')
def employee_dashboard(username):
    conn = get_db_connection()
    # Fetch time entries for the logged-in employee
    entries = conn.execute(
        'SELECT * FROM time_entries WHERE LOWER(REPLACE(username, " ", "")) = ?',
        (username.lower().replace(" ", ""),)
    ).fetchall()
    
    # Fetch invoices for the logged-in employee
    invoices = conn.execute(
        'SELECT invoice_number, date, total_hours, total_payment, filename, sent '
        'FROM invoices WHERE LOWER(REPLACE(username, " ", "")) = ? ORDER BY date DESC',
        (username.lower().replace(" ", ""),)
    ).fetchall()
    conn.close()

    # Prepare time entries for rendering
    entry_list = []
    for entry in entries:
        entry_data = {
            'date': entry['date'],
            'start_time': entry['start_time'],
            'end_time': entry['end_time'],
            'total_hours': round((datetime.strptime(entry['end_time'], "%H:%M") - datetime.strptime(entry['start_time'], "%H:%M") - timedelta(minutes=30)).seconds / 3600.0, 2)
        }
        entry_list.append(entry_data)
    
    # Prepare invoices for rendering
    invoice_list = []
    for invoice in invoices:
        invoice_data = {
            'invoice_number': invoice['invoice_number'],
            'date': invoice['date'],
            'total_hours': invoice['total_hours'],
            'total_payment': invoice['total_payment'],
            'filename': invoice['filename'],
            'sent': invoice['sent']
        }
        invoice_list.append(invoice_data)

    return render_template('employee_dashboard.html', username=username, entries=entry_list, invoices=invoice_list)


@app.route('/add_time_entry', methods=['POST'])
def add_time_entry():
    username = request.form.get('username').lower()
    date = request.form.get('date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    if not all([username, date, start_time, end_time]):
        return jsonify({'error': 'All fields are required!'}), 400

    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO time_entries (username, date, start_time, end_time) VALUES (?, ?, ?, ?)',
            (username, date, start_time, end_time)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('employee_dashboard', username=username))
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_time_entry', methods=['POST'])
def delete_time_entry():
    username = request.form.get('username').strip().lower().replace(" ", "_")
    date = request.form.get('date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM time_entries 
            WHERE username = ? AND date = ? AND start_time = ? AND end_time = ?
        ''', (username, date, start_time, end_time))

        if cursor.rowcount == 0:
            message = "No matching entry found to delete."
        else:
            conn.commit()
            message = "Entry deleted successfully."

        conn.close()
        return jsonify({'message': message}), 200

    except sqlite3.Error as e:
        return jsonify({'error': f"Error during deletion: {e}"}), 500

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice_route():
    username = request.form.get('username').strip().lower().replace(" ", "")

    if not username:
        app.logger.error("Username is required for generating an invoice")
        return jsonify({'error': 'Username is required'}), 400

    try:
        conn = get_db_connection()

        # Fetch time entries
        entries = conn.execute(
            'SELECT date, start_time, end_time FROM time_entries WHERE LOWER(REPLACE(username, " ", "")) = ?',
            (username,)
        ).fetchall()

        if not entries:
            app.logger.info(f"No time entries found for user {username}")
            return jsonify({'error': 'No time entries found for this user'}), 400

        # Invoice data
        invoice_date = datetime.now().strftime("%Y-%m-%d")
        invoice_number = conn.execute(
            'SELECT COALESCE(MAX(invoice_number), 0) + 1 FROM invoices'
        ).fetchone()[0]

        # Process timesheet data
        timesheet_data = [
            (entry['date'], entry['start_time'], entry['end_time'],
             round((datetime.strptime(entry['end_time'], "%H:%M") - datetime.strptime(entry['start_time'], "%H:%M") - timedelta(minutes=30)).seconds / 3600.0, 2))
            for entry in entries
        ]
        total_hours = sum(entry[3] for entry in timesheet_data)

        # Generate invoice
        filepath = generate_invoice(invoice_number, username, {
            "Company Name": "GOAT Removals",
            "Address": "19 O'Neile Crescent, NSW, 2170, Australia",
            "Phone": "+61 2 1234 5678"
        }, timesheet_data, total_hours)

        # Check if the file exists
        if not filepath or not os.path.exists(filepath):
            app.logger.error(f"Invoice generation failed. File not found: {filepath}")
            return jsonify({'error': f"Invoice file not found at {filepath}"}), 500

        # Save to database (Store only the filename)
        conn.execute(
            """
            INSERT INTO invoices (invoice_number, username, date, total_hours, total_payment, filename, sent)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                invoice_number,
                username,
                invoice_date,
                total_hours,
                total_hours * 30,
                os.path.basename(filepath)  # Save only the filename
            )
        )
        conn.commit()

        app.logger.info(f"Invoice {invoice_number} generated successfully for user {username}")
        return send_file(filepath, as_attachment=True)

    except Exception as e:
        app.logger.error(f"Failed to generate invoice for {username}: {str(e)}")
        return jsonify({'error': f"Failed to generate invoice: {str(e)}"}), 500

    finally:
        conn.close()


@app.route('/employee_invoices/<username>', methods=['GET'])
def employee_invoices(username):
    conn = get_db_connection()
    try:
        query = 'SELECT invoice_number, date, total_hours, total_payment, filename FROM invoices WHERE username = ? ORDER BY date DESC'
        invoices = conn.execute(query, (username,)).fetchall()
        invoices_list = [{'invoice_number': invoice['invoice_number'], 'date': invoice['date'], 'total_hours': invoice['total_hours'], 'total_payment': invoice['total_payment'], 'filename': invoice['filename']} for invoice in invoices]
        return jsonify(invoices_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/send_invoice_to_db', methods=['POST'])
def send_invoice_to_db():
    username = request.form.get('username')
    if not username:
        return jsonify({'error': 'Username is required'}), 400

    conn = get_db_connection()

    try:
        # Retrieve the most recent unsent invoice for the user
        existing_invoice = conn.execute(
            'SELECT * FROM invoices WHERE username = ? AND sent = 0 ORDER BY date DESC LIMIT 1',
            (username,)
        ).fetchone()

        if not existing_invoice:
            return jsonify({'error': 'No generated invoice found for this user to send.'}), 400

        # Mark the invoice as sent
        conn.execute(
            'UPDATE invoices SET sent = 1 WHERE invoice_number = ?',
            (existing_invoice['invoice_number'],)
        )
        conn.commit()

        return jsonify({'message': f"Invoice {existing_invoice['invoice_number']} sent successfully!"}), 200

    except sqlite3.Error as e:
        return jsonify({'error': f"Database error: {e}"}), 500

    finally:
        conn.close()

        
@app.route('/download_invoice/<filename>')
def download_invoice(filename):
    try:
        # Define the directory where invoices are stored
        directory = "/tmp/invoices"
        file_path = os.path.join(directory, filename)

        # Log the directory and file name for debugging
        app.logger.info(f"Looking for file in directory: {directory}")
        app.logger.info(f"Requested file: {filename}")

        # Check if the file exists
        if not os.path.exists(file_path):
            app.logger.error(f"File not found: {file_path}")
            return jsonify({"error": "File not found"}), 404

        # Serve the file
        return send_from_directory(directory, filename, as_attachment=False)
    except Exception as e:
        app.logger.error(f"Error serving the invoice: {str(e)}")
        return jsonify({"error": f"Error serving the invoice: {str(e)}"}), 500


    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
