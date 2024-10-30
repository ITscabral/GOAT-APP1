from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import sqlite3
import os
from datetime import datetime, timedelta
from invoice_generator import generate_invoice, open_invoice

app = Flask(__name__)

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

    # Include the employee's name in the invoices list
    invoice_list = []
    for invoice in invoices:
        employee_name = next((emp['username'] for emp in employees if emp['username'] == invoice['username']), 'Unknown')
        invoice_data = {
            'invoice_number': invoice['invoice_number'],
            'username': employee_name,
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


@app.route('/generate_invoice', methods=['POST'])
def generate_invoice_route():
    username = request.form.get('username')

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    # Fetch time entries for this employee
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

    # Generate Invoice Number
    conn = get_db_connection()
    invoice_number = conn.execute('SELECT COALESCE(MAX(invoice_number), 0) + 1 FROM invoices').fetchone()[0]
    conn.close()

    # Generate Invoice PDF
    target_directory = os.path.join(os.getcwd(), "invoices")
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
    filename = f"Invoice_{invoice_number}_{username}.pdf"
    filepath = os.path.join(target_directory, filename)

    # Use your existing `generate_invoice` function to create the PDF
    result_filepath = generate_invoice(invoice_number, username, {}, timesheet_data, total_hours)

    # Validate if the file was created
    if result_filepath is None or not os.path.exists(result_filepath):
        return jsonify({'error': 'Failed to generate invoice or file not found'}), 500

    # Save Invoice Metadata
    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO invoices (invoice_number, username, date, total_hours, total_payment, filename) VALUES (?, ?, ?, ?, ?, ?)',
            (invoice_number, username, datetime.now().strftime("%Y-%m-%d"), total_hours, total_hours * 30, filename))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500

    # Return a success response
    return jsonify({'success': True, 'invoice_number': invoice_number})

@app.route('/send_invoice', methods=['POST'])
def send_invoice():
    username = request.form.get('username')
    invoice_number = request.form.get('invoice_number')

    if not username or not invoice_number:
        return jsonify({'error': 'Username and Invoice number are required'}), 400

    # Fetch invoice filename from database
    conn = get_db_connection()
    invoice = conn.execute('SELECT filename FROM invoices WHERE invoice_number = ? AND username = ?', (invoice_number, username)).fetchone()
    conn.close()

    if invoice:
        filepath = os.path.join(os.getcwd(), "invoices", invoice['filename'])
        if os.path.exists(filepath):
            # TODO: Implement email sending logic with attachment
            # For now, simply return success for testing purposes
            return jsonify({'message': 'Invoice sent successfully!'}), 200
        else:
            return jsonify({'error': 'Invoice file not found'}), 404
    else:
        return jsonify({'error': 'Invoice not found'}), 404


@app.route('/open_invoice/<filename>')
def open_invoice(filename):
    target_directory = os.path.join(os.getcwd(), "invoices")
    filepath = os.path.join(target_directory, filename)

    if os.path.exists(filepath):
        try:
            return send_file(filepath, as_attachment=False)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Invoice file not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

@app.route('/open_invoice/<filename>')
def open_invoice(filename):
    filepath = os.path.join(os.getcwd(), "invoices", filename)
    if os.path.exists(filepath):
        try:
            return send_file(filepath, as_attachment=False)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Invoice file not found'}), 404

@app.route('/get_employees', methods=['GET'])
def get_employees():
    conn = get_db_connection()
    employees = conn.execute('SELECT username, role FROM users WHERE role = "employee"').fetchall()
    conn.close()
    employee_list = [{'username': emp['username'], 'role': emp['role']} for emp in employees]
    return jsonify(employee_list)

@app.route('/get_time_entries', methods=['GET'])
def get_time_entries():
    conn = get_db_connection()
    entries = conn.execute('SELECT * FROM time_entries').fetchall()
    conn.close()
    time_entries_list = [
        {'username': entry['username'], 'date': entry['date'], 'start_time': entry['start_time'], 'end_time': entry['end_time']}
        for entry in entries
    ]
    return jsonify(time_entries_list)

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
