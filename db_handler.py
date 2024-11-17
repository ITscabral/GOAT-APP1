import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self, db_path="timesheet.db"):
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file '{db_path}' not found.")
        self.connect_db()
        self.ensure_schema_updates()

    def connect_db(self):
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            print("Connected to SQLite database successfully.")
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise

    def query(self, sql, params=()):
        with self.connection:
            cursor = self.connection.execute(sql, params)
            return cursor.fetchall()

    def execute(self, sql, params=()):
        with self.connection:
            cursor = self.connection.execute(sql, params)
            self.connection.commit()
            return cursor.rowcount

    def ensure_schema_updates(self):
        """Ensure all schema updates are applied, such as adding missing columns."""
        self.add_sent_column()

    def add_sent_column(self):
        """Add 'sent' column to invoices table if it does not exist."""
        cursor = self.connection.cursor()
        cursor.execute("PRAGMA table_info(invoices)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'sent' not in columns:
            cursor.execute("ALTER TABLE invoices ADD COLUMN sent INTEGER DEFAULT 0")
            print("Added 'sent' column to invoices table.")
            self.connection.commit()

    def get_next_invoice_number(self):
        sql = "SELECT COALESCE(MAX(invoice_number), 0) + 1 AS next_id FROM invoices"
        result = self.query(sql)
        return result[0]['next_id']

    def save_invoice(self, invoice_number, username, total_hours, total_payment, filename):
        """Save the invoice details to the invoices table."""
        try:
            print(f"Saving invoice {invoice_number} for user {username}")
            self.execute(
                "INSERT INTO invoices (invoice_number, username, date, total_hours, total_payment, filename, sent) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (invoice_number, username, datetime.now().strftime("%Y-%m-%d"), total_hours, total_payment, filename, 0)
            )
            print("Invoice saved successfully.")
        except sqlite3.Error as e:
            print(f"Error saving invoice: {e}")

    def mark_invoice_as_sent(self, invoice_number):
        sql = "UPDATE invoices SET sent = 1 WHERE invoice_number = ?"
        self.execute(sql, (invoice_number,))
        print(f"Invoice {invoice_number} marked as sent.")

    def __del__(self):
        self.connection.close()
