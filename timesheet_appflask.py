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

    # User table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            phone_number TEXT
        )
    ''')

    # Time entries table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS time_entries (
            username TEXT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')

    # Invoices table
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

    # Commit changes and close connection
    conn.commit()
    conn.close()

# Run initialization
initialize_db()

# Function to get a database connection
def get_db_connection():
    conn = sqlite3.connect('timesheet.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Home route
@app.route('/')
def home():
    return render_template('index.html')

# Login route with POST method
@app.route('/login', methods=['POST'])
def login():
    try:
        username = request.form.get('username').strip().lower().replace(" ", "")
        password = request.form.get('password')

        # Check if username and password are provided
        if not username or not password:
            return jsonify({'message': 'Username and password are required'}), 400

        conn = get_db_connection()
        query = "SELECT role FROM users WHERE LOWER(REPLACE(username, ' ', '')) = ? AND password = ?"
        user = conn.execute(query, (username, password)).fetchone()
        conn.close()

        if user:
            role = user['role']
            # Redirect based on role
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'employee':
                return redirect(url_for('employee_dashboard', username=username))
        else:
            return jsonify({'message': 'Invalid credentials'}), 401

    except sqlite3.Error as e:
        return jsonify({'error': f"Database error during login: {e}"}), 500

# Admin dashboard route
@app.route('/admin_dashboard')
def admin_dashboard():
    conn = get_db_connection()
    
    teams = {
        "Team 1 - Jackson C & Lucas C": ["Jackson Carneiro", "Lucas Cabral"],
        "Team 2 - Bruno V & Thallys C": ["Bruno Vianello", "Thallys Carvalho"],
        "Team 3 - Michel S & Giulliano C": ["Michel Silva", "Giulliano Cabral"],
        "Team 4 - Pedro C & Caio H": ["Pedro Cadenas", "Caio Henrique"],
    }

    # Fetch employees, time entries, and invoices
    employees = conn.execute('SELECT * FROM users WHERE role = "employee"').fetchall()
    entries = conn.execute('SELECT * FROM time_entries').fetchall()
    invoices = conn.execute('SELECT * FROM invoices').fetchall()
    conn.close()

    # Process employee list by team
    employee_list = []
    for team_name, team_members in teams.items():
        for member in team_members:
            employee_data = next((emp for emp in employees if emp['username'].strip().title() == member), None)
            employee_list.append({
                'username': member,
                'team': team_name,
                'role': employee_data['role'] if employee_data else None
            })

    # Process time entry list
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

    # Process invoice list
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

# Employee dashboard route
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

# Add employee route
@app.route('/add_employee', methods=['POST'])
def add_employee():
    name = request.form.get('name')
    role = request.form.get('role')
    phone_number = request.form.get('phone_number')

    # Check if fields are completed
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

# Add time entry route
@app.route('/add_time_entry', methods=['POST'])
def add_time_entry():
    username = request.form.get('username').lower()
    date = request.form.get('date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    # Check if fields are filled
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

# Delete time entry route
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
        return render_template('delete_entry_form.html', message=message)

    except sqlite3.Error as e:
        return render_template('delete_entry_form.html', message=f"Error: {e}")

# Run application
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
