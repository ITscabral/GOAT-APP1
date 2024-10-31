from flask import Flask, render_template, request, redirect, url_for, session
from database import Database
from timesheet_app import TimesheetApp
from admin_dashboard import AdminDashboard
from employee_dashboard import EmployeeDashboard
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

db = Database()
timesheet_app = TimesheetApp(db)
admin_dashboard = AdminDashboard(db)
employee_dashboard = EmployeeDashboard(db)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = db.query('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    if user:
        session['username'] = username
        role = user[0][3]  # Assuming role is in the 4th column of the users table
        if role == 'admin':
            return redirect(url_for('admin_dashboard_view'))
        elif role == 'employee':
            return redirect(url_for('employee_dashboard_view'))
        else:
            return "Access denied: role not recognized."
    else:
        return "Invalid credentials, please try again."

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin_dashboard_view():
    if 'username' in session and db.is_admin(session['username']):
        teams = admin_dashboard.get_teams()
        return render_template('admin_dashboard.html', teams=teams)
    else:
        return redirect(url_for('index'))

@app.route('/employee')
def employee_dashboard_view():
    if 'username' in session and not db.is_admin(session['username']):
        entries = employee_dashboard.get_entries(session['username'])
        return render_template('employee_dashboard.html', entries=entries)
    else:
        return redirect(url_for('index'))

@app.route('/add_worker', methods=['POST'])
def add_worker():
    if 'username' in session and db.is_admin(session['username']):
        username = request.form['username']
        role = request.form['role']
        admin_dashboard.add_worker(username, role)
        return redirect(url_for('admin_dashboard_view'))
    else:
        return redirect(url_for('index'))

@app.route('/add_entry', methods=['POST'])
def add_entry():
    if 'username' in session and not db.is_admin(session['username']):
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        employee_dashboard.add_entry(session['username'], date, start_time, end_time)
        return redirect(url_for('employee_dashboard_view'))
    else:
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
