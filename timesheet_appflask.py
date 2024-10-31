import os
import uuid
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from dotenv import load_dotenv
import logging
from twilio_service import send_sms
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# Initialize Flask app with secret key
app = Flask(__name__)
app.secret_key = "your_secret_key"

# Set up logging for debugging and information
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Define paths for the database and invoices folder
DATABASE_PATH = "timesheet.db"
INVOICES_FOLDER = "invoices"

# Ensure the invoices folder exists
if not os.path.exists(INVOICES_FOLDER):
    os.makedirs(INVOICES_FOLDER)
    logger.info("Invoices folder created.")

def get_db_connection():
    """Establish a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/", methods=["GET", "POST"])
def login():
    """Display the login page and handle user authentication."""
    logger.info("Rendering login page.")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        logger.info(f"Login attempt for username: {username}")

        # Validate user credentials
        conn = get_db_connection()
        user = conn.execute("SELECT role FROM users WHERE LOWER(username) = ? AND password = ?", (username.lower(), password)).fetchone()
        conn.close()

        if user:
            role = user["role"]
            logger.info(f"User '{username}' logged in with role '{role}'")
            if role == 'admin':
                return redirect(url_for("admin_dashboard"))
            elif role == 'employee':
                return redirect(url_for("employee_dashboard", username=username))
        else:
            logger.warning(f"Failed login for username: {username}")
            flash("Invalid credentials.")
    return render_template("login.html")

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    """Handle password reset requests and send a token via SMS."""
    logger.info("Rendering password reset page.")
    if request.method == "POST":
        username = request.form["username"]
        conn = get_db_connection()
        user = conn.execute("SELECT phone_number FROM users WHERE LOWER(username) = ?", (username.lower(),)).fetchone()
        conn.close()

        if user and user["phone_number"]:
            phone_number = format_phone_number(user["phone_number"])
            token = uuid.uuid4().hex[:8]  # Generate reset token
            conn = get_db_connection()
            conn.execute("UPDATE users SET reset_token = ? WHERE LOWER(username) = ?", (token, username.lower()))
            conn.commit()
            conn.close()

            logger.info(f"Reset token '{token}' generated for '{username}'")
            send_sms(phone_number, f"Your password reset token is: {token}")
            flash("Reset token sent via SMS.")
            return redirect(url_for("password_change"))
        else:
            logger.warning(f"Phone number not found for user '{username}'.")
            flash("User not found or phone number missing.")
    return render_template("reset_password.html")

@app.route("/password_change", methods=["GET", "POST"])
def password_change():
    """Allow users to change their password using a token."""
    logger.info("Rendering password change page.")
    if request.method == "POST":
        token = request.form["token"]
        new_password = request.form["new_password"]
        logger.info(f"Password change attempt with token: {token}")

        # Verify the reset token
        conn = get_db_connection()
        user = conn.execute("SELECT username FROM users WHERE reset_token = ?", (token,)).fetchone()
        if user:
            conn.execute("UPDATE users SET password = ?, reset_token = NULL WHERE reset_token = ?", (new_password, token))
            conn.commit()
            conn.close()
            logger.info(f"Password updated for user '{user['username']}'")
            flash("Password changed successfully!")
            return redirect(url_for("login"))
        else:
            conn.close()
            logger.warning(f"Invalid reset token: {token}")
            flash("Invalid reset token.")
    return render_template("password_change.html")

@app.route("/generate_invoice/<username>", methods=["GET", "POST"])
def generate_invoice(username):
    """Generate a PDF invoice for the specified user."""
    logger.info(f"Generating invoice for user: {username}")
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if not user:
        logger.warning(f"User '{username}' not found.")
        flash("User not found.")
        return redirect(url_for("employee_dashboard", username=username))

    invoice_number = uuid.uuid4().hex[:8]
    filename = f"Invoice_{invoice_number}_{username}.pdf"
    filepath = os.path.join(INVOICES_FOLDER, filename)

    # Create the PDF using ReportLab
    c = canvas.Canvas(filepath, pagesize=A4)
    add_invoice_header(c, invoice_number, username)
    add_invoice_content(c, username)
    c.save()
    
    logger.info(f"Invoice for '{username}' saved as '{filename}'.")
    flash("Invoice generated successfully.")
    return redirect(url_for("view_invoice", filename=filename))

def add_invoice_header(c, invoice_number, username):
    """Add header details to the invoice PDF."""
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, 800, f"Invoice #{invoice_number}")
    c.setFont("Helvetica", 10)
    c.drawString(30, 770, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    c.drawString(30, 755, f"Client: {username}")
    logger.info(f"Header added for '{username}'.")

def add_invoice_content(c, username):
    """Add content, including timesheet details and total payment, to the PDF."""
    timesheet_data = fetch_timesheet_data(username)
    y = 700
    for entry in timesheet_data:
        c.drawString(30, y, f"Date: {entry['date']} - {entry['start']} to {entry['end']} - Hours: {entry['hours']}")
        y -= 20

    total_hours = sum(entry['hours'] for entry in timesheet_data)
    hourly_rate = 30.0
    total_payment = total_hours * hourly_rate
    c.drawString(30, y - 20, f"Total Hours: {total_hours}")
    c.drawString(30, y - 40, f"Hourly Rate: ${hourly_rate}")
    c.drawString(30, y - 60, f"Total Payment: ${total_payment}")
    logger.info(f"Invoice content for '{username}' added.")

def fetch_timesheet_data(username):
    """Fetch timesheet data for the specified user."""
    # Replace with actual DB query for real data
    return [
        {"date": "2023-11-01", "start": "09:00", "end": "17:00", "hours": 7.5},
        {"date": "2023-11-02", "start": "09:00", "end": "17:00", "hours": 7.5}
    ]

@app.route("/view_invoice/<filename>")
def view_invoice(filename):
    """Display the generated invoice as a PDF."""
    filepath = os.path.join(INVOICES_FOLDER, filename)
    if os.path.exists(filepath):
        logger.info(f"Displaying invoice '{filename}' for user.")
        return send_file(filepath, as_attachment=False)
    else:
        logger.error(f"Invoice file not found: {filename}")
        flash("Invoice file not found.")
        return redirect(url_for("employee_dashboard"))

@app.route("/admin_dashboard")
def admin_dashboard():
    """Render the admin dashboard."""
    logger.info("Accessed admin dashboard.")
    return "Welcome to the Admin Dashboard!"

@app.route("/employee_dashboard/<username>")
def employee_dashboard(username):
    """Render the employee dashboard for the logged-in user."""
    logger.info(f"Accessed employee dashboard for '{username}'")
    return f"Welcome, {username}! This is your Employee Dashboard."

def format_phone_number(phone_number):
    """Format phone number to international format."""
    phone_number = str(phone_number).strip()
    if phone_number.startswith("0"):
        phone_number = f"+61{phone_number[1:]}"
    elif not phone_number.startswith("+"):
        phone_number = f"+{phone_number}"
    logger.info(f"Formatted phone number: {phone_number}")
    return phone_number

def initialize_database():
    """Initialize database with required tables if they do not exist."""
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    phone_number TEXT,
                    reset_token TEXT)''')
    conn.commit()
    conn.close()
    logger.info("Database initialized with 'users' table.")

# Initialize the database
initialize_database()

if __name__ == "__main__":
    logger.info("Starting the Flask application.")
    app.run(debug=True)