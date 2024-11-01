from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import sqlite3
import os
from datetime import datetime, timedelta
from invoice_generator import generate_invoice
from db_handler import Database

app = Flask(__name__)

# Initialize the database and create tables if they don't exist
def initialize_db():
    conn = sqlite3.connect('timesheet.db', check_same_thread=False)
    cursor = conn.cursor()

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
            username TEXT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_number INTEGER PRIMARY KEY,
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

# Call the initialization function
initialize_db()

def get_db_connection():
    conn = sqlite3.connect('timesheet.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/test_db')
def test_db():
    conn = get_db_connection()
    try:
        users = conn.execute("SELECT * FROM users").fetchall()
        conn.close()
        if users:
            return jsonify({'message': "User data retrieved successfully", 'data': [dict(user) for user in users]})
        else:
            return jsonify({'message': "No user data found in the database"})
    except Exception as e:
        conn.close()
        return jsonify({'error': f"Database test failed: {str(e)}"}), 500

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    try:
        # Normalize username
        username = request.form.get('username').strip().lower().replace(" ", "")
        password = request.form.get('password')
        
        if not username or not password:
            print("[DEBUG] Username or password missing in form data")
            return jsonify({'message': 'Username and password are required'}), 400

        print(f"[DEBUG] Login attempt with normalized Username: '{username}' and Password: '{password}'")
        
        # Connect to the database
        conn = get_db_connection()
        query = "SELECT role FROM users WHERE LOWER(REPLACE(username, ' ', '')) = ? AND password = ?"
        
        # Execute query with debug logs
        print(f"[DEBUG] Executing login query: {query} with params: ({username}, {password})")
        user = conn.execute(query, (username, password)).fetchone()
        conn.close()

        if user:
            role = user['role']
            print(f"[DEBUG] Login successful for user with role: {role}")
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'employee':
                return redirect(url_for('employee_dashboard', username=username))
        else:
            print("[DEBUG] Invalid credentials: No match found in database")
            return jsonify({'message': 'Invalid credentials'}), 401

    except sqlite3.Error as e:
        print(f"[ERROR] Database error during login: {e}")
        return jsonify({'error': f"Database error during login: {e}"}), 500
    except Exception as e:
        print(f"[ERROR] Unexpected error during login: {e}")
        return jsonify({'error': f"Unexpected error during login: {e}"}), 500


@app.route('/admin_dashboard')
def admin_dashboard():
    conn = get_db_connection()
    teams = {
        "Team 1": ["jackson_carneiro", "lucas_cabral"],
        "Team 2": ["bruno_vianello", "thallys_carvalho"],
        "Team 3": ["michel_silva", "giulliano_cabral"],
        "Team 4": ["pedro_cadenas", "caio_henrique"],
    }

    employees = conn.execute('SELECT * FROM users WHERE role = "employee"').fetchall()
    entries = conn.execute('SELECT * FROM time_entries').fetchall()
    invoices = conn.execute('''
        SELECT invoices.*, users.username as employee_name
        FROM invoices
        JOIN users ON invoices.username = users.username
    ''').fetchall()
    conn.close()

    employee_list = []
    for team_name, team_members in teams.items():
        for member in team_members:
            employee_data = next((emp for emp in employees if emp['username'] == member), None)
            if employee_data:
                employee_list.append({'username': member, 'team': team_name, 'role': employee_data['role']})
            else:
                employee_list.append({'username': member, 'team': team_name, 'role': None})

    entry_list = []
    for entry in entries:
        entry_data = {
            'username': entry['username'],
            'date': entry['date'],
            'start_time': entry['start_time'],
            'end_time': entry['end_time'],
            'total_hours': round((datetime.strptime(entry['end_time'], "%H:%M") - datetime.strptime(entry['start_time'], "%H:%M") - timedelta(minutes=30)).seconds / 3600.0, 2)
        }
        entry_list.append(entry_data)

    invoice_list = []
    for invoice in invoices:
        invoice_data = {
            'invoice_number': invoice['invoice_number'],
            'username': invoice['employee_name'],
            'date': invoice['date'],
            'total_hours': invoice['total_hours'],
            'total_payment': invoice['total_payment'],
            'filename': invoice['filename']
        }
        invoice_list.append(invoice_data)

    return render_template('admin_dashboard.html', teams=teams.keys(), employees=employee_list, entries=entry_list, invoices=invoice_list)

@app.route('/employee_dashboard/<username>')
def employee_dashboard(username):
    conn = get_db_connection()
    entries = conn.execute(
        'SELECT * FROM time_entries WHERE LOWER(REPLACE(username, " ", "")) = ?', 
        (username.lower().replace(" ", ""),)
    ).fetchall()
    conn.close()
    
    entry_list = []
    for entry in entries:
        entry_data = {
            'date': entry['date'],
            'start_time': entry['start_time'],
            'end_time': entry['end_time'],
            'total_hours': round((datetime.strptime(entry['end_time'], "%H:%M") - datetime.strptime(entry['start_time'], "%H:%M") - timedelta(minutes=30)).seconds / 3600.0, 2)
        }
        entry_list.append(entry_data)
    return render_template('employee_dashboard.html', username=username, entries=entry_list)

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

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice_route():
    username = request.form.get('username')

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    conn = get_db_connection()
    entries = conn.execute('SELECT date, start_time, end_time FROM time_entries WHERE username = ?', (username,)).fetchall()
    conn.close()

    if not entries:
        return jsonify({'error': 'No time entries found for this user'}), 400

    timesheet_data = [
        (entry['date'], entry['start_time'], entry['end_time'],
         round((datetime.strptime(entry['end_time'], "%H:%M") - datetime.strptime(entry['start_time'], "%H:%M") - timedelta(minutes=30)).seconds / 3600.0, 2))
        for entry in entries
    ]
    total_hours = sum(entry[3] for entry in timesheet_data)

    conn = get_db_connection()
    invoice_number = conn.execute('SELECT COALESCE(MAX(invoice_number), 0) + 1 FROM invoices').fetchone()[0]
    conn.close()

    target_directory = os.path.join(os.getcwd(), "invoices")
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
    filename = f"Invoice_{invoice_number}_{username}.pdf"
    filepath = os.path.join(target_directory, filename)

    result_filepath = generate_invoice(invoice_number, username, {}, timesheet_data, total_hours)
    if result_filepath is None or not os.path.exists(result_filepath):
        return jsonify({'error': 'Failed to generate invoice or file not found'}), 500

    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO invoices (invoice_number, username, date, total_hours, total_payment, filename) VALUES (?, ?, ?, ?, ?, ?)',
            (invoice_number, username, datetime.now().strftime("%Y-%m-%d"), total_hours, total_hours * 30, filename)
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        return jsonify({'error': f'Failed to save invoice data: {str(e)}'}), 500

    return send_file(filepath, as_attachment=False, mimetype='application/pdf')

@app.route('/download_timesheet_db')
def download_timesheet_db():
    try:
        return send_file('timesheet.db', as_attachment=True)
    except Exception as e:
        return jsonify({'error': f"Could not find or download the file: {str(e)}"}), 500
        
@app.route('/send_invoice', methods=['POST'])
def send_invoice():
    # Placeholder functionality - replace with actual logic to send invoice
    username = request.form.get('username')
    invoice_number = request.form.get('invoice_number')
    # Implement the logic to send the invoice, e.g., via email or other service

    # For demonstration purposes, return a success message
    return jsonify({'message': f'Invoice {invoice_number} sent successfully to {username}'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
