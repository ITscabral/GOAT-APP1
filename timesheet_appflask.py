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

    employees = conn.execute('SELECT * FROM users WHERE role = "employee"').fetchall()
    entries = conn.execute('SELECT * FROM time_entries').fetchall()

    # Explicitly query for all invoices and ensure they are linked correctly with users
    invoices = conn.execute('''
        SELECT invoices.*, users.username as employee_name
        FROM invoices
        JOIN users ON invoices.username = users.username
    ''').fetchall()

    conn.close()

    # Process employee list by team
    employee_list = []
    for team_name, team_members in teams.items():
        for member in team_members:
            # Match usernames with case-insensitivity and format for display
            employee_data = next((emp for emp in employees if emp['username'].strip().title() == member), None)
            if employee_data:
                employee_list.append({
                    'username': member,
                    'team': team_name,
                    'role': employee_data['role']
                })
            else:
                employee_list.append({
                    'username': member,
                    'team': team_name,
                    'role': None
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
            'username': ' '.join(invoice['employee_name'].strip().title().split()),
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
        return render_template('delete_entry_form.html', message=message)

    except sqlite3.Error as e:
        return render_template('delete_entry_form.html', message=f"Error: {e}")

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice_route():
    username = request.form.get('username')

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    conn = get_db_connection()

    # Fetch time entries for the employee
    entries = conn.execute(
        'SELECT date, start_time, end_time FROM time_entries WHERE username = ?',
        (username,)
    ).fetchall()

    if not entries:
        conn.close()
        return jsonify({'error': 'No time entries found for this user'}), 400

    # Prepare timesheet data and calculate total hours
    timesheet_data = [
        (entry['date'], entry['start_time'], entry['end_time'],
         round((datetime.strptime(entry['end_time'], "%H:%M") - datetime.strptime(entry['start_time'], "%H:%M") - timedelta(minutes=30)).seconds / 3600.0, 2))
        for entry in entries
    ]
    total_hours = sum(entry[3] for entry in timesheet_data)
    invoice_date = datetime.now().strftime("%Y-%m-%d")

    # Fetch the existing invoice count for this user on the same date
    invoice_count = conn.execute(
        'SELECT COUNT(*) FROM invoices WHERE username = ? AND date = ?',
        (username, invoice_date)
    ).fetchone()[0]

    # Create a unique invoice number by appending the count for that day
    invoice_number = f"{invoice_date.replace('-', '')}_{invoice_count + 1}"

    # Generate the invoice PDF (assuming the function returns a file path)
    company_info = {
        "Company Name": "GOAT Removals",
        "Address": "123 Business St, Sydney, Australia",
        "Phone": "+61 2 1234 5678"
    }
    filepath = generate_invoice(invoice_number, username, company_info, timesheet_data, total_hours)

    if filepath is None or not os.path.exists(filepath):
        conn.close()
        print("[ERROR] Invoice file was not created.")
        return jsonify({'error': 'Failed to generate invoice or file not found'}), 500

    # Save the invoice to the database with the unique identifier
    try:
        conn.execute(
            'INSERT INTO invoices (invoice_number, username, date, total_hours, total_payment, filename) VALUES (?, ?, ?, ?, ?, ?)',
            (invoice_number, username, invoice_date, total_hours, total_hours * 30, filepath)
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.close()
        print(f"[ERROR] Database error while saving invoice: {e}")
        return jsonify({'error': f'Failed to save invoice data: {str(e)}'}), 500
    finally:
        conn.close()

    if os.path.exists(filepath):
        print(f"[DEBUG] Serving the invoice file: {filepath}")
        return send_file(filepath, as_attachment=True)
    else:
        print(f"[ERROR] File not found at path: {filepath}")
        return jsonify({'error': 'File not found after creation'}), 500

@app.route('/download_timesheet_db')
def download_timesheet_db():
    try:
        return send_file('timesheet.db', as_attachment=True)
    except Exception as e:
        return jsonify({'error': f"Could not find or download the file: {str(e)}"}), 500

@app.route('/send_invoice_to_db', methods=['POST'])
def send_invoice_to_db():
    username = request.form.get('username')
    invoice_number = request.form.get('invoice_number')

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    # Generate or retrieve the invoice file for this user
    conn = get_db_connection()
    entries = conn.execute(
        'SELECT date, start_time, end_time FROM time_entries WHERE username = ?',
        (username,)
    ).fetchall()

    if not entries:
        conn.close()
        return jsonify({'error': 'No time entries found for this user'}), 400

    # Prepare timesheet data and calculate total hours
    timesheet_data = [
        (entry['date'], entry['start_time'], entry['end_time'],
         round((datetime.strptime(entry['end_time'], "%H:%M") - datetime.strptime(entry['start_time'], "%H:%M") - timedelta(minutes=30)).seconds / 3600.0, 2))
        for entry in entries
    ]
    total_hours = sum(entry[3] for entry in timesheet_data)

    # Get today's date for invoice date
    invoice_date = datetime.now().strftime("%Y-%m-%d")

    # Check for duplicate invoice by looking for an identical date, username, and total_hours
    existing_invoice = conn.execute(
        'SELECT * FROM invoices WHERE username = ? AND date = ? AND total_hours = ?',
        (username, invoice_date, total_hours)
    ).fetchone()

    if existing_invoice:
        conn.close()
        return jsonify({'error': 'An identical invoice already exists for this date.'}), 400

    # If no duplicate is found, proceed to create a new invoice
    invoice_number = conn.execute('SELECT COALESCE(MAX(invoice_number), 0) + 1 FROM invoices').fetchone()[0]

    # Company details
    company_info = {
        "Company Name": "GOAT Removals",
        "Address": "123 Business St, Sydney, Australia",
        "Phone": "+61 2 1234 5678"
    }

    # Generate the invoice PDF
    filepath = generate_invoice(invoice_number, username, company_info, timesheet_data, total_hours)

    # Verify that the PDF was successfully created
    if filepath is None or not os.path.exists(filepath):
        conn.close()
        return jsonify({'error': 'Failed to generate invoice or file not found'}), 500

    # Save the invoice to the database
    try:
        conn.execute(
            'INSERT INTO invoices (invoice_number, username, date, total_hours, total_payment, filename) VALUES (?, ?, ?, ?, ?, ?)',
            (invoice_number, username, invoice_date, total_hours, total_hours * 30, filepath)
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.close()
        return jsonify({'error': f'Failed to save invoice data: {str(e)}'}), 500
    finally:
        conn.close()

    # Confirm the invoice is sent to the database
    return jsonify({'message': f'Invoice {invoice_number} sent successfully to admin dashboard'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
