import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
import uuid
from database import Database
from twilio_service import send_sms

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

    def create_form(self, label_text, row, show=None):
        tk.Label(self.root, text=f"{label_text}:").grid(row=row, column=0, padx=5, pady=5)
        entry = tk.Entry(self.root, show=show) if show else tk.Entry(self.root)
        entry.grid(row=row, column=1, padx=5, pady=5)
        setattr(self, f"{label_text.lower()}_entry", entry)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        user = self.db.query("SELECT role FROM users WHERE username = ? AND password = ?", (username, password))
        if user:
            role = user[0][0]
            if role == 'admin':
                self.admin_dashboard()
            elif role == 'employee':
                self.employee_dashboard(username)
            else:
                messagebox.showerror("Access Denied", "You don't have access!")
        else:
            messagebox.showerror("Login Failed", "Invalid credentials!")

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
        user = self.db.query("SELECT phone_number FROM users WHERE username = ?", (username,))
        if user and user[0][0]:
            phone_number = self.format_phone_number(user[0][0])
            token = str(uuid.uuid4())[:8]
            self.db.execute("UPDATE users SET reset_token = ? WHERE username = ?", (token, username))
            send_sms(phone_number, f"Your password reset token is: {token}")
            messagebox.showinfo("Success", "Reset token sent via SMS.")
            self.password_change_window()
        else:
            messagebox.showerror("Error", "User not found or phone number missing.")

    def format_phone_number(self, phone_number):
        phone_number = str(phone_number).strip()
        if phone_number.startswith('0'):
            return f"+61{phone_number[1:]}"
        elif not phone_number.startswith('+'):
            return f"+{phone_number}"
        return phone_number

    def admin_dashboard(self):
        self.clear_window()
        tk.Label(self.root, text="Admin Dashboard", font=("Arial", 16)).grid(row=0, columnspan=3, pady=10)
        self.add_employee_form()

    def add_employee_form(self):
        tk.Label(self.root, text="Add New Employee", font=("Arial", 12)).grid(row=4, column=0, columnspan=3, pady=10)
        self.name_entry = self.create_input("Name", 5)
        self.main_role_combobox = self.create_combobox("Main Role", ["Driver", "Offsider"], 6)
        self.rate_entry = self.create_input("Rate per Hour", 7)
        self.abn_entry = self.create_input("ABN", 8)
        self.phone_number_entry = self.create_input("Phone Number", 9)
        tk.Button(self.root, text="Add Employee", command=self.add_employee).grid(row=10, columnspan=3, pady=10)

    def add_employee(self):
        name = self.name_entry.get()
        main_role = self.main_role_combobox.get()
        rate = self.rate_entry.get()
        abn = self.abn_entry.get()
        phone_number = self.phone_number_entry.get()

        if not all([name, main_role, rate, abn, phone_number]):
            messagebox.showerror("Error", "All fields are required!")
            return

        try:
            float(rate)
            self.db.execute(
                "INSERT INTO users (username, password, role, main_role, rate_per_hour, abn, phone_number) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)", (name, '123', 'employee', main_role, rate, abn, phone_number)
            )
            send_sms(phone_number, f"Welcome {name}. Password: 123. Change it here: [link].")
            messagebox.showinfo("Success", "Employee added successfully!")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Employee already exists!")

    def create_input(self, label, row):
        tk.Label(self.root, text=f"{label}:").grid(row=row, column=0, padx=5, pady=5)
        entry = tk.Entry(self.root)
        entry.grid(row=row, column=1, padx=5, pady=5)
        return entry

    def create_combobox(self, label, values, row):
        tk.Label(self.root, text=f"{label}:").grid(row=row, column=0, padx=5, pady=5)
        combobox = ttk.Combobox(self.root, values=values)
        combobox.grid(row=row, column=1, padx=5, pady=5)
        return combobox
