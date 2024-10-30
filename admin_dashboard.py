import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import subprocess  # For native PDF opening
from twilio.rest import Client  # Twilio for SMS notifications
import os  # To check file existence
from invoice_generator import generate_invoice, open_invoice  # Import your invoice functions

# Twilio credentials
TWILIO_ACCOUNT_SID = 'REDACTED'
TWILIO_AUTH_TOKEN = 'REDACTED'
TWILIO_PHONE_NUMBER = 'REDACTED'


class AdminDashboard:
    def __init__(self, root, db):
        self.root = root
        self.db = db
        self.selected_invoice_filename = None  # Track the selected invoice filename
        self.open_button = None  # Initialize open_button
        self.show_dashboard()

    def show_dashboard(self):
        self.clear_window()

        tk.Label(self.root, text="Admin Dashboard", font=("Arial", 16)).grid(row=0, columnspan=4, pady=10)

        # Team and Employee Selection
        tk.Label(self.root, text="Select Team:").grid(row=1, column=0, sticky='e')
        self.team_combobox = ttk.Combobox(self.root, values=["Team 1", "Team 2", "Team 3", "Team 4"])
        self.team_combobox.grid(row=1, column=1, padx=5, pady=5)
        self.team_combobox.bind("<<ComboboxSelected>>", self.show_team_entries)

        tk.Label(self.root, text="Select Employee:").grid(row=1, column=2, sticky='e')
        self.employee_combobox = ttk.Combobox(self.root, values=self.get_employees())
        self.employee_combobox.grid(row=1, column=3, padx=5, pady=5)
        self.employee_combobox.bind("<<ComboboxSelected>>", self.show_employee_entries)

        # Time Entries and Invoice Display
        tk.Label(self.root, text="Time Entries", font=("Arial", 12)).grid(row=2, columnspan=4, pady=10)
        self.team_tree = self.create_tree_view(["Username", "Date", "Start", "End", "Total Hours"], 3)

        tk.Label(self.root, text="Previous Invoices", font=("Arial", 12)).grid(row=4, columnspan=4, pady=10)
        self.invoice_tree = self.create_tree_view(["Invoice #", "Date", "Total Hours", "Total Payment"], 5)
        self.invoice_tree.bind("<<TreeviewSelect>>", self.on_invoice_selected)

        # Open Invoice Button
        self.open_button = tk.Button(self.root, text="Open Invoice", command=self.open_selected_invoice, state=tk.DISABLED)
        self.open_button.grid(row=6, columnspan=4, pady=10)

        self.add_employee_form()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def get_employees(self):
        employees = self.db.query("SELECT username FROM users WHERE role = 'employee'")
        return [emp[0] for emp in employees]

    def show_team_entries(self, event):
        selected_team = self.team_combobox.get()
        self.refresh_tree_view(self.team_tree, selected_team)

    def show_employee_entries(self, event):
        selected_employee = self.employee_combobox.get()
        self.refresh_tree_view(self.team_tree, selected_employee)
        self.show_previous_invoices(selected_employee)

    def refresh_tree_view(self, tree, filter_value):
        for row in tree.get_children():
            tree.delete(row)

        entries = self.db.query(
            "SELECT u.username, t.date, t.start_time, t.end_time "
            "FROM users u JOIN time_entries t ON u.username = t.username "
            "WHERE u.username LIKE ? OR u.team LIKE ?",
            (f"%{filter_value}%", f"%{filter_value}%")
        )

        for username, date, start, end in entries:
            total_hours = self.calculate_hours(start, end)
            tree.insert("", tk.END, values=(username, date, start, end, total_hours))

    def show_previous_invoices(self, employee):
        """Display the previous invoices for the selected employee."""
        for row in self.invoice_tree.get_children():
            self.invoice_tree.delete(row)

        invoices = self.db.query(
            "SELECT invoice_number, date, total_hours, total_payment, filename "
            "FROM invoices WHERE username = ? ORDER BY date DESC",
            (employee,)
        )

        for invoice in invoices:
            print(f"Invoice Data Before Insertion: {invoice}")  # Debug print statement
            # Insert invoice data into Treeview
            self.invoice_tree.insert("", tk.END, values=invoice)

    def on_invoice_selected(self, event):
        """Enable the 'Open Invoice' button and store the selected filename."""
        selected_item = self.invoice_tree.selection()
        if selected_item:
            invoice = self.invoice_tree.item(selected_item)['values']
            if len(invoice) >= 5:
                self.selected_invoice_filename = invoice[4]  # Assuming the filename is the fifth element in the row
                self.open_button.config(state=tk.NORMAL)
            else:
                self.selected_invoice_filename = None
                self.open_button.config(state=tk.DISABLED)
                messagebox.showerror("Error", "Filename not found in the selected invoice data.")

    def open_selected_invoice(self):
        """Open the selected invoice in the native PDF viewer."""
        if not self.selected_invoice_filename:
            messagebox.showerror("Error", "No invoice selected.")
            return

        if os.path.exists(self.selected_invoice_filename):
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(self.selected_invoice_filename)
                elif 'Darwin' in os.uname().sysname:  # macOS
                    subprocess.Popen(['open', self.selected_invoice_filename])
                else:  # Linux
                    subprocess.Popen(['xdg-open', self.selected_invoice_filename])
                print(f"Attempting to open invoice: {self.selected_invoice_filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open invoice: {e}")
                print(f"Failed to open invoice: {e}")
        else:
            messagebox.showerror("Error", f"Invoice file not found: {self.selected_invoice_filename}")
            print(f"Invoice file not found: {self.selected_invoice_filename}")

    def calculate_hours(self, start, end):
        start_dt = datetime.strptime(start, "%H:%M")
        end_dt = datetime.strptime(end, "%H:%M")
        return round((end_dt - start_dt - timedelta(minutes=30)).seconds / 3600, 2)

    def add_employee_form(self):
        tk.Label(self.root, text="Add New Employee", font=("Arial", 12)).grid(row=7, column=0, columnspan=4, pady=10)

        self.name_entry = self.create_input("Name", 8)
        self.main_role_combobox = self.create_combobox("Main Role", ["Driver", "Offsider", "Dock Receiver", "One-Day Labour"], 9)
        self.rate_entry = self.create_input("Rate per Hour", 10)
        self.abn_entry = self.create_input("ABN", 11)
        self.phone_number_entry = self.create_input("Phone Number", 12)

        tk.Button(self.root, text="Add Employee", command=self.add_employee).grid(row=13, columnspan=4, pady=10)

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
            self.send_sms(f"+61{phone_number[1:]}", f"Welcome {name}! Your default password is '123'. Please change it.")
            messagebox.showinfo("Success", "Employee added successfully!")
            self.employee_combobox['values'] = self.get_employees()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add employee: {e}")

    def send_sms(self, to_number, message):
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            client.messages.create(body=message, from_=TWILIO_PHONE_NUMBER, to=to_number)
            messagebox.showinfo("Success", f"SMS sent to {to_number}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send SMS: {e}")

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

    def create_tree_view(self, columns, row):
        tree = ttk.Treeview(self.root, columns=columns, show='headings', height=10)
        for col in columns:
            tree.heading(col, text=col)
        tree.grid(row=row, column=0, columnspan=4, padx=10, pady=5)
        return tree
