import os
import tkinter as tk
from tkinter import messagebox
import uuid
import sqlite3
from dotenv import load_dotenv
from twilio.rest import Client

class Database:
    def __init__(self, db_path="C:\\Users\\Lucas Cabral\\PycharmProjects\\Python Mini Curso\\GOAT APP\\timesheet.db"):
        if not os.path.exists(db_path):
            print(f"Database file '{db_path}' not found.")
            raise FileNotFoundError("The specified database file does not exist.")
        try:
            self.connection = sqlite3.connect(db_path)
            self.cursor = self.connection.cursor()
            print("Connected to SQLite database successfully.")
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")

    def query(self, sql, params=()):
        try:
            self.cursor.execute(sql, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"SQL Query Error: {e}")
            return []

    def execute(self, sql, params=()):
        try:
            self.cursor.execute(sql, params)
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"SQL Execution Error: {e}")

class TimesheetApp:
    def __init__(self, root):
        print("Initializing TimesheetApp...")
        self.db = Database()
        self.root = root
        self.root.title("GOAT Removals - Login")
        self.login_window()

    def login_window(self):
        self.clear_window()
        self.create_form("Username", row=0)
        self.create_form("Password", row=1, show='*')
        tk.Button(self.root, text="Login", command=self.login).grid(row=2, columnspan=2, pady=10)
        tk.Button(self.root, text="Forgot Password?", command=self.reset_password_window).grid(row=3, columnspan=2, pady=10)

    def create_form(self, label, row, show=None):
        tk.Label(self.root, text=f"{label}:").grid(row=row, column=0, padx=5, pady=5)
        entry = tk.Entry(self.root, show=show)
        entry.grid(row=row, column=1, padx=5, pady=5)
        setattr(self, f"{label.lower()}_entry", entry)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        print(f"Login attempt with Username: {username} and Password: {password}")
        try:
            user = self.db.query("SELECT role FROM users WHERE LOWER(username) = ? AND password = ?", (username.lower(), password))
            if user:
                role = user[0][0]
                if role == 'admin':
                    self.open_admin_dashboard()
                elif role == 'employee':
                    self.open_employee_dashboard(username)
            else:
                print("Invalid credentials")
                messagebox.showerror("Login Failed", "Invalid credentials!")
        except sqlite3.Error as e:
            print(f"Exception during login: {e}")
            messagebox.showerror("Error", "An error occurred during login.")

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def reset_password_window(self):
        self.clear_window()
        tk.Label(self.root, text="Reset Password", font=("Arial", 16)).grid(row=0, columnspan=2, pady=10)
        self.create_form("Username", row=1)
        tk.Button(self.root, text="Send Reset Token", command=self.send_reset_token).grid(row=2, columnspan=2, pady=10)

    def send_reset_token(self):
        username = self.username_entry.get()
        user = self.db.query("SELECT phone_number FROM users WHERE LOWER(username) = ?", (username.lower(),))
        if user and user[0][0]:
            phone_number = str(user[0][0]).strip()
            if phone_number.startswith('0'):
                phone_number = f"+61{phone_number[1:]}"
            elif not phone_number.startswith('+'):
                phone_number = f"+{phone_number}"
            token = uuid.uuid4().hex[:8]
            self.db.execute("UPDATE users SET reset_token = ? WHERE LOWER(username) = ?", (token, username.lower()))
            self.send_sms(phone_number, f"Your password reset token is: {token}")
            messagebox.showinfo("Success", "Reset token sent via SMS.")
            self.password_change_window()
        else:
            messagebox.showerror("Error", "User not found or phone number missing.")

    def password_change_window(self):
        self.clear_window()
        tk.Label(self.root, text="Enter Reset Token", font=("Arial", 16)).grid(row=0, columnspan=2, pady=10)
        self.create_form("Reset Token", row=1)
        self.create_form("New Password", row=2, show='*')
        tk.Button(self.root, text="Change Password", command=self.change_password).grid(row=3, columnspan=2, pady=10)

    def change_password(self):
        token = self.reset_token_entry.get()
        new_password = self.new_password_entry.get()
        user = self.db.query("SELECT username FROM users WHERE reset_token = ?", (token,))
        if user:
            self.db.execute("UPDATE users SET password = ?, reset_token = NULL WHERE reset_token = ?", (new_password, token))
            messagebox.showinfo("Success", "Password changed successfully!")
            self.login_window()
        else:
            messagebox.showerror("Error", "Invalid reset token!")

    def send_sms(self, to_number, message):
        load_dotenv()
        TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
        TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
        TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
            messagebox.showerror("SMS Error", "Twilio credentials are not properly set in the environment variables.")
            return
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            sms = client.messages.create(body=message, from_=TWILIO_PHONE_NUMBER, to=to_number)
            print(f"SMS sent successfully. SID: {sms.sid}")
        except Exception as e:
            messagebox.showerror("SMS Error", f"Failed to send SMS: {e}")

    def open_admin_dashboard(self):
        print("Admin dashboard opened.")  # Replace with AdminDashboard(self.root, self.db)

    def open_employee_dashboard(self, username):
        print("Employee dashboard opened.")  # Replace with EmployeeDashboard(self.root, self.db, username)

if __name__ == "__main__":
    root = tk.Tk()
    app = TimesheetApp(root)
    root.mainloop()
