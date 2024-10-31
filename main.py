from flask import Flask, render_template, request, redirect, url_for, flash
import uuid
import logging
from dotenv import load_dotenv
from database import Database
from twilio_service import send_sms  # Import send_sms from twilio_service

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Replace with a secure key
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Database
db = Database()  # Initialize the database connection
logger.info("Database initialized.")

# Load environment variables for Twilio (if needed elsewhere in app)
load_dotenv()

@app.route("/", methods=["GET", "POST"])
def login():
    """Display the login page and handle user login."""
    logger.info("Rendering login page.")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        logger.info(f"Login attempt with Username: {username}")

        user = db.query("SELECT role FROM users WHERE LOWER(username) = ? AND password = ?", (username.lower(), password))
        if user:
            role = user[0][0]
            logger.info(f"User '{username}' logged in as '{role}'")
            if role == 'admin':
                return redirect(url_for("admin_dashboard"))
            elif role == 'employee':
                return redirect(url_for("employee_dashboard", username=username))
        else:
            logger.warning(f"Login failed for username: {username}")
            flash("Invalid credentials")
    return render_template("login.html")

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    """Display the password reset page and send a reset token via SMS."""
    logger.info("Rendering password reset page.")
    if request.method == "POST":
        username = request.form["username"]
        user = db.query("SELECT phone_number FROM users WHERE LOWER(username) = ?", (username.lower(),))

        if user and user[0][0]:
            phone_number = format_phone_number(user[0][0])
            token = uuid.uuid4().hex[:8]
            db.execute("UPDATE users SET reset_token = ? WHERE LOWER(username) = ?", (token, username.lower()))
            logger.info(f"Reset token generated for user '{username}': {token}")
            send_sms(phone_number, f"Your password reset token is: {token}")  # Use send_sms from twilio_service
            flash("Reset token sent via SMS.")
            return redirect(url_for("password_change"))
        else:
            logger.warning(f"User '{username}' not found or phone number missing.")
            flash("User not found or phone number missing.")
    return render_template("reset_password.html")

@app.route("/password_change", methods=["GET", "POST"])
def password_change():
    """Handle password reset with a token."""
    logger.info("Rendering password change page.")
    if request.method == "POST":
        token = request.form["token"]
        new_password = request.form["new_password"]
        logger.info(f"Password change attempt with token: {token}")

        user = db.query("SELECT username FROM users WHERE reset_token = ?", (token,))
        if user:
            db.execute("UPDATE users SET password = ?, reset_token = NULL WHERE reset_token = ?", (new_password, token))
            logger.info(f"Password changed successfully for user '{user[0][0]}'.")
            flash("Password changed successfully!")
            return redirect(url_for("login"))
        else:
            logger.warning(f"Invalid reset token used: {token}")
            flash("Invalid reset token.")
    return render_template("password_change.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    """Admin dashboard view."""
    logger.info("Accessed admin dashboard.")
    return "Welcome to the Admin Dashboard!"

@app.route("/employee_dashboard/<username>")
def employee_dashboard(username):
    """Employee dashboard view."""
    logger.info(f"Accessed employee dashboard for user: {username}")
    return f"Welcome, {username}! This is your Employee Dashboard."

def format_phone_number(phone_number):
    """Format phone number for Australian numbers."""
    phone_number = str(phone_number).strip()
    if phone_number.startswith("0"):
        phone_number = f"+61{phone_number[1:]}"
    elif not phone_number.startswith("+"):
        phone_number = f"+{phone_number}"
    logger.info(f"Formatted phone number: {phone_number}")
    return phone_number

if __name__ == "__main__":
    logger.info("Starting the Flask application.")
    app.run(debug=True)