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
    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
    conn.close()
    if user:
        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user['role'] == 'employee':
            return redirect(url_for('employee_dashboard', username=username))
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

    return render_template(
        'admin_dashboard.html',
        teams=teams.keys(),
        employees=employee_list,
        entries=entry_list,
        invoices=invoices
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
    username = request.form.get('username')
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

def generate_invoice(invoice_number, employee_name, company_info, timesheet_data, total_hours, hourly_rate=30.0):
    """Generate a professional PDF invoice."""

    # Step 1: Define the specific folder path
    target_directory = os.path.join(os.getcwd(), "invoices")
    print(f"[INFO] Target directory: {target_directory}")

    # Step 2: Ensure the directory exists
    if not os.path.exists(target_directory):
        print("[INFO] Directory does not exist, creating it...")
        os.makedirs(target_directory)

    # Step 3: Create the filename with the full path
    filename = os.path.join(target_directory, f"Invoice_{invoice_number}_{employee_name}.pdf")
    print(f"[INFO] Full path to invoice: {filename}")

    try:
        # Initialize PDF canvas
        print(f"[INFO] Generating PDF at {filename}")
        c = canvas.Canvas(filename, pagesize=A4)

        # Optional: Add a logo if it exists
        logo_path = "company_logo.png"
        if os.path.exists(logo_path):
            c.drawImage(logo_path, 30, 770, width=120, height=80)
        else:
            print("[WARNING] Logo not found, skipping.")

        # Add Company Info
        c.setFont("Helvetica-Bold", 12)
        c.drawString(150, 800, company_info.get("Company Name", "GOAT Removals"))
        c.setFont("Helvetica", 10)
        c.drawString(150, 780, company_info.get("Address", "123 Business St, Sydney, Australia"))
        c.drawString(150, 765, f"Phone: {company_info.get('Phone', '+61 2 1234 5678')}")

        # Add Invoice Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(230, 720, f"Invoice #{invoice_number}")

        # Add Employee Name and Date
        date_generated = datetime.now().strftime('%Y-%m-%d %A')
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, 690, f"Employee: {employee_name}")
        c.setFont("Helvetica", 10)
        c.drawString(30, 670, f"Date Generated: {date_generated}")

        # Add Table Data
        y = 640
        for entry in timesheet_data:
            date, start, end, hours = entry
            weekday = datetime.strptime(date, "%Y-%m-%d").strftime('%A')
            c.setFont("Helvetica", 10)
            c.drawString(30, y, f"{date} ({weekday})")
            c.drawString(150, y, start)
            c.drawString(250, y, end)
            c.drawString(350, y, f"{hours:.2f}")
            y -= 20

        # Summary and Footer
        total_payment = total_hours * hourly_rate
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30, y - 30, f"Total Hours: {total_hours:.2f}")
        c.drawString(30, y - 50, f"Hourly Rate: ${hourly_rate:.2f}")
        c.drawString(30, y - 70, f"Total Payment: ${total_payment:.2f}")

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawString(30, 50, "Thank you for your work! If you have any questions, contact our office.")

        # Save the PDF
        c.save()
        print(f"[SUCCESS] PDF saved at {filename}")

        # Validate the file exists after saving
        if os.path.exists(filename):
            print(f"[INFO] File exists: {filename}")
            return filename
        else:
            raise FileNotFoundError(f"File not found at: {filename}")

    except Exception as e:
        print(f"[ERROR] Invoice generation failed: {e}")
        return None


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
