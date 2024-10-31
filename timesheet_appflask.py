from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import sqlite3
import os
from datetime import datetime, timedelta
import random

app = Flask(__name__)

# Function to initialize the database and create tables if they don't exist
def initialize_db():
    conn = sqlite3.connect('timesheet.db', check_same_thread=False)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            phone_number TEXT,
            reset_code TEXT
        )
    ''')

    # Create time_entries table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS time_entries (
            username TEXT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')

    # Create invoices table
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

    # Insert sample data into users table
    users_data = [
        ('lucas_cabral', '123', 'employee', '1234567890', None),
        ('jackson_carneiro', '123', 'employee', '1234567891', None),
        ('michel_silva', '123', 'admin', '1234567892', None),
        ('bruno_vianello', '123', 'employee', '1234567893', None),
        ('thallys_carvalho', '123', 'employee', '1234567894', None),
        ('giulliano_cabral', '123', 'employee', '1234567895', None),
        ('pedro_cadenas', '123', 'employee', '1234567896', None),
        ('caio_henrique', '123', 'employee', '1234567897', None)
    ]

    cursor.executemany('INSERT OR IGNORE INTO users (username, password, role, phone_number, reset_code) VALUES (?, ?, ?, ?, ?)', users_data)

    conn.commit()
    conn.close()

# Call the initialization function
initialize_db()

def get_db_connection():
    conn = sqlite3.connect('timesheet.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username').strip()
    password = request.form.get('password').strip()

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    except sqlite3.OperationalError as e:
        return jsonify({'error': f"Database error: {e}. Please check your database structure."}), 500
    finally:
        conn.close()

    if user and user['password'] == password:
        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user['role'] == 'employee':
            return redirect(url_for('employee_dashboard', username=user['username']))
    return jsonify({'message': 'Invalid credentials'}), 401

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
    invoices = conn.execute('SELECT * FROM invoices').fetchall()

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
            'username': invoice['username'],
            'date': invoice['date'],
            'total_hours': invoice['total_hours'],
            'total_payment': invoice['total_payment'],
            'filename': invoice['filename']
        }
        invoice_list.append(invoice_data)

    return render_template(
        'admin_dashboard.html',
        teams=teams.keys(),
        employees=employee_list,
        entries=entry_list,
        invoices=invoice_list
    )

@app.route('/employee_dashboard/<username>')
def employee_dashboard(username):
    conn = get_db_connection()
    entries = conn.execute('SELECT * FROM time_entries WHERE username = ?', (username,)).fetchall()
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
    username = request.form.get('username').strip()
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
    username = request.form.get('username').strip()

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

    invoice_number = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"Invoice_{invoice_number}_{username}.pdf"
    filepath = os.path.join(os.getcwd(), "invoices", filename)

    if not os.path.exists(os.path.dirname(filepath)):
        os.makedirs(os.path.dirname(filepath))

    with open(filepath, 'w') as f:
        f.write(f"Invoice for {username}\n")
        f.write(f"Total Hours: {total_hours}\n")
        f.write(f"Total Payment: ${total_hours * 30}\n")

    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO invoices (invoice_number, username, date, total_hours, total_payment, filename) VALUES (?, ?, ?, ?, ?, ?)',
            (invoice_number, username, datetime.now().strftime("%Y-%m-%d"), total_hours, total_hours * 30, filename)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'invoice_number': invoice_number})
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/send_invoice', methods=['POST'])
def send_invoice_route():
    username = request.form.get('username').strip()
    invoice_number = request.form.get('invoice_number')

    if not username or not invoice_number:
        return jsonify({'error': 'Username and invoice number are required'}), 400

    conn = get_db_connection()
    invoice = conn.execute('SELECT * FROM invoices WHERE invoice_number = ?', (invoice_number,)).fetchone()
    conn.close()

    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    return jsonify({'success': True, 'message': 'Invoice sent successfully'})

@app.route('/open_invoice/<filename>')
def open_invoice(filename):
    invoice_path = os.path.join(os.getcwd(), "invoices", filename)
    if os.path.exists(invoice_path):
        return send_file(invoice_path, as_attachment=False)
    return jsonify({'error': 'Invoice not found'}), 404

@app.route('/add_employee', methods=['POST'])
def add_employee():
    name = request.form.get('name').strip()
    role = request.form.get('role').strip()
    phone_number = request.form.get('phone_number').strip()

    if not all([name, role, phone_number]):
        return jsonify({'error': 'All fields are required!'}), 400

    username =
