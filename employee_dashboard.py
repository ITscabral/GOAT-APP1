import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
from datetime import datetime, timedelta
from invoice_generator import generate_invoice, open_invoice

class EmployeeDashboard:
    def __init__(self, root, db, username):
        self.root = root
        self.db = db
        self.username = username
        self.invoice_generated = False  # Track if the invoice has been generated
        self.show_dashboard()

    def show_dashboard(self):
        self.clear_window()
        tk.Label(self.root, text=f"Welcome, {self.username}!", font=("Arial", 16)).grid(row=0, columnspan=2, pady=10)
        self.create_time_entry_ui()

        self.preview_button = tk.Button(
            self.root, text="Generate & Preview Invoice", command=self.generate_invoice,
            bg="#4CAF50", fg="white", font=("Arial", 12)
        )
        self.preview_button.grid(row=8, column=0, pady=10)

        self.send_button = tk.Button(
            self.root, text="Send Invoice", command=self.send_invoice,
            bg="#2196F3", fg="white", font=("Arial", 12), state=tk.DISABLED
        )
        self.send_button.grid(row=8, column=1, pady=10)

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def create_time_entry_ui(self):
        tk.Label(self.root, text="Select Date:").grid(row=1, column=0, padx=5, pady=5)
        self.date_entry = DateEntry(self.root, date_pattern='yyyy-mm-dd')
        self.date_entry.grid(row=1, column=1, padx=5, pady=5)

        self.create_time_inputs()
        self.create_employee_buttons()
        self.entry_tree = self.create_tree_view(["Date", "Start", "End", "Hours Worked"], 6)
        self.refresh_entries()

    def create_time_inputs(self):
        tk.Label(self.root, text="Start Time (HH:MM):").grid(row=3, column=0, padx=5, pady=5)
        self.start_time_entry = tk.Entry(self.root)
        self.start_time_entry.grid(row=3, column=1, padx=5, pady=5)

        tk.Label(self.root, text="End Time (HH:MM):").grid(row=4, column=0, padx=5, pady=5)
        self.end_time_entry = tk.Entry(self.root)
        self.end_time_entry.grid(row=4, column=1, padx=5, pady=5)

    def create_employee_buttons(self):
        tk.Button(self.root, text="Save", command=self.save_time_entry).grid(row=5, column=0, pady=5)
        tk.Button(self.root, text="Clear Selected", command=self.clear_selected_entry).grid(row=5, column=1, pady=5)

    def save_time_entry(self):
        date = self.date_entry.get()
        start = self.start_time_entry.get()
        end = self.end_time_entry.get()
        try:
            datetime.strptime(start, "%H:%M")
            datetime.strptime(end, "%H:%M")
            self.db.execute(
                "INSERT INTO time_entries (username, date, start_time, end_time) VALUES (?, ?, ?, ?)",
                (self.username, date, start, end)
            )
            self.refresh_entries()
        except ValueError:
            messagebox.showerror("Invalid Time", "Enter time in HH:MM format!")

    def clear_selected_entry(self):
        selected_item = self.entry_tree.selection()
        if selected_item:
            entry = self.entry_tree.item(selected_item)['values']
            self.db.execute(
                "DELETE FROM time_entries WHERE date = ? AND start_time = ? AND end_time = ?",
                (entry[0], entry[1], entry[2])
            )
            self.entry_tree.delete(selected_item)

    def refresh_entries(self):
        for row in self.entry_tree.get_children():
            self.entry_tree.delete(row)
        entries = self.db.query(
            "SELECT date, start_time, end_time FROM time_entries WHERE username = ?",
            (self.username,)
        )
        for date, start, end in entries:
            total = self.calculate_hours(start, end)
            self.entry_tree.insert("", tk.END, values=(date, start, end, total))

    def calculate_hours(self, start, end):
        start_dt = datetime.strptime(start, "%H:%M")
        end_dt = datetime.strptime(end, "%H:%M")
        return round((end_dt - start_dt - timedelta(minutes=30)).seconds / 3600, 2)

    def create_tree_view(self, columns, row):
        tree = ttk.Treeview(self.root, columns=columns, show='headings', height=10)
        for col in columns:
            tree.heading(col, text=col)
        tree.grid(row=row, column=0, columnspan=2, padx=10, pady=5)
        return tree

    def generate_invoice(self):
        timesheet_data = [
            (entry[0], entry[1], entry[2], self.calculate_hours(entry[1], entry[2]))
            for entry in self.db.query(
                "SELECT date, start_time, end_time FROM time_entries WHERE username = ?",
                (self.username,)
            )
        ]
        total_hours = sum(entry[3] for entry in timesheet_data)
        invoice_number = self.db.get_next_invoice_number()
        filename = generate_invoice(invoice_number, self.username, {}, timesheet_data, total_hours)
        self.db.save_invoice(invoice_number, self.username, total_hours, total_hours * 30, filename)
        open_invoice(filename)
        self.invoice_generated = True
        self.send_button.config(state=tk.NORMAL)

    def send_invoice(self):
        messagebox.showinfo("Invoice Sent", "Invoice sent successfully!")
        self.invoice_generated = False
        self.send_button.config(state=tk.DISABLED)