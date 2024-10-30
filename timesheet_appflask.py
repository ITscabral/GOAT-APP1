from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import sqlite3
import os
from datetime import datetime, timedelta
from invoice_generator import generate_invoice, open_invoice

app = Flask(__name__)

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import sqlite3
import os
from datetime import datetime, timedelta
from invoice_generator import generate_invoice, open_invoice

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
            phone_number TEXT
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
    username = request.form.get('username').lower()  # Convert to lowercase for case-insensitive match
    password = request.form.get('password')
    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE LOWER(username) = ?', (username,)).fetchone()
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
        "Team 1": ["Jackson Carneiro", "Lucas Cabral"],
        "Team 2": ["Bruno Vianello", "Thallys Carvalho"],
        "Team 3": ["Michel Silva", "Giulliano Cabral"],
        "Team 4": ["Pedro Cadenas", "Caio Henrique"],
    }

    employees = conn.execute('SELECT * FROM users WHERE role = "employee"').fetchall()
    entries = conn.execute('SELECT * FROM time_entries').fetchall()

    # Join invoices with users to get employee names
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
            'total_hours': round((datetime.strptime(entry['end_time'], "%H:%M") - datetime.strptime(entry['start_time'],
                                                                                                    "%H:%M") - timedelta(
                minutes=30)).seconds / 3600.0, 2)
        }
        entry_list.append(entry_data)

    # Include the employee's name in the invoices list
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

    return render_template(
        'admin_dashboard.html',
        teams=teams.keys(),
        employees=employee_list,
        entries=entry_list,
        invoices=invoice_list  # Pass updated invoice list with employee names
    )

@app.route('/employee_dashboard/<username>')
def employee_dashboard(username):
    conn = get_db_connection()
    entries = conn.execute('SELECT * FROM time_entries WHERE LOWER(username) = ?', (username.lower(),)).fetchall()
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
    username = request.form.get('username').lower()  # Convert to lowercase for case-insensitive match
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

@app.route('/get_invoices', methods=['GET'])
def get_invoices():
    conn = get_db_connection()
    invoices = conn.execute('SELECT * FROM invoices').fetchall()
    conn.close()
    invoice_list = [
        {
            'invoice_number': invoice['invoice_number'],
            'username': invoice['username'],
            'date': invoice['date'],
            'total_hours': invoice['total_hours'],
            'total_payment': invoice['total_payment'],
            'filename': invoice['filename']
        }
        for invoice in invoices
    ]
    return jsonify(invoice_list)

@app.route('/add_employee', methods=['POST'])
def add_employee():
    name = request.form.get('name')
    role = request.form.get('role')
    rate = request.form.get('rate')
    abn = request.form.get('abn')
    phone_number = request.form.get('phone_number')

    if not all([name, role, rate, abn, phone_number]):
        return jsonify({'error': 'All fields are required!'}), 400

    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO users (username, password, role, phone_number) VALUES (?, ?, ?, ?)',
            (name, '123', role, phone_number)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Employee added successfully!'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Employee with this username already exists!'}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
