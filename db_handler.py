import sqlite3
import os

class Database:
    def __init__(self, db_path="timesheet.db"):
        print(f"Attempting to connect to database at: {db_path}")
        if not os.path.exists(db_path):
            print(f"Database file '{db_path}' not found.")
            raise FileNotFoundError("The specified database file does not exist.")

        try:
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.cursor = self.connection.cursor()
            print("Connected to SQLite database successfully.")
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")

    def query(self, sql, params=()):
        try:
            print(f"Executing SQL Query: {sql} with params: {params}")
            self.cursor.execute(sql, params)
            result = self.cursor.fetchall()
            print(f"Query result: {result}")
            return result
        except sqlite3.Error as e:
            print(f"SQL Query Error: {e}")
            return []

    def execute(self, sql, params=()):
        try:
            print(f"Executing SQL Command: {sql} with params: {params}")
            self.cursor.execute(sql, params)
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"SQL Execution Error: {e}")

    def get_next_invoice_number(self):
        """Retrieve the next invoice number by checking the max value in the invoices table."""
        try:
            self.cursor.execute("SELECT COALESCE(MAX(invoice_number), 0) + 1 FROM invoices")
            result = self.cursor.fetchone()
            next_invoice_number = result[0] if result else 1
            print(f"Next invoice number: {next_invoice_number}")
            return next_invoice_number
        except sqlite3.Error as e:
            print(f"Error fetching next invoice number: {e}")
            return None

    def save_invoice(self, invoice_number, username, total_hours, total_payment, filename):
        """Save the invoice details to the invoices table."""
        try:
            print(f"Saving invoice {invoice_number} for user {username}")
            self.execute(
                "INSERT INTO invoices (invoice_number, username, date, total_hours, total_payment, filename) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (invoice_number, username, datetime.now().strftime("%Y-%m-%d"), total_hours, total_payment, filename)
            )
            print("Invoice saved successfully.")
        except sqlite3.Error as e:
            print(f"Error saving invoice: {e}")

