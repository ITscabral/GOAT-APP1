import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self, db_path="timesheet.db"):
        """Initialize the database connection and ensure schema updates."""
        self.db_path = db_path

        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file '{db_path}' not found.")

        self.connect_db()
        self.ensure_schema_updates()

    def connect_db(self):
        """Establish connection to the SQLite database."""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            print("Connected to SQLite database successfully.")
        except sqlite3.Error as e:
            raise ConnectionError(f"Database connection error: {e}")

    def query(self, sql, params=()):
        """Execute a SELECT query and return the results."""
        try:
            with self.connection:
                cursor = self.connection.execute(sql, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Query error: {e}")
            return []

    def execute(self, sql, params=()):
        """Execute an INSERT/UPDATE/DELETE query."""
        try:
            with self.connection:
                cursor = self.connection.execute(sql, params)
                self.connection.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            print(f"Execution error: {e}")
            return 0

    def ensure_schema_updates(self):
        """Ensure all schema updates are applied, such as adding missing columns."""
        try:
            self.add_sent_column()
        except sqlite3.Error as e:
            print(f"Error ensuring schema updates: {e}")

    def add_sent_column(self):
        """Add 'sent' column to invoices table if it does not exist."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("PRAGMA table_info(invoices)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'sent' not in columns:
                cursor.execute("ALTER TABLE invoices ADD COLUMN sent INTEGER DEFAULT 0")
                print("Added 'sent' column to invoices table.")
                self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error adding 'sent' column: {e}")

    def get_next_invoice_number(self):
        """Get the next available invoice number."""
        try:
            sql = "SELECT COALESCE(MAX(invoice_number), 0) + 1 AS next_id FROM invoices"
            result = self.query(sql)
            return result[0]['next_id'] if result else 1
        except sqlite3.Error as e:
            print(f"Error fetching next invoice number: {e}")
            return 1

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
        """Mark an invoice as sent."""
        try:
            sql = "UPDATE invoices SET sent = 1 WHERE invoice_number = ?"
            rows_updated = self.execute(sql, (invoice_number,))
            if rows_updated > 0:
                print(f"Invoice {invoice_number} marked as sent.")
            else:
                print(f"No invoice found with number {invoice_number} to mark as sent.")
        except sqlite3.Error as e:
            print(f"Error marking invoice as sent: {e}")

    def __del__(self):
        """Close the database connection."""
        try:
            self.connection.close()
        except AttributeError:
            pass
