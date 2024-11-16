import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self, db_path="timesheet.db"):
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file '{db_path}' not found.")
        self.connect_db()

    def connect_db(self):
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Optional: This makes fetch operations return dictionaries
            print("Connected to SQLite database successfully.")
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise

    def query(self, sql, params=()):
        with self.connection:
            try:
                cursor = self.connection.execute(sql, params)
                return cursor.fetchall()
            except sqlite3.Error as e:
                print(f"SQL Query Error: {e}")
                raise

    def execute(self, sql, params=()):
        with self.connection:
            try:
                cursor = self.connection.execute(sql, params)
                self.connection.commit()
                return cursor.rowcount
            except sqlite3.Error as e:
                print(f"SQL Execution Error: {e}")
                raise

    def get_next_invoice_number(self):
        sql = "SELECT COALESCE(MAX(invoice_number), 0) + 1 AS next_id FROM invoices"
        try:
            result = self.query(sql)
            return result[0]['next_id']
        except Exception as e:
            print(f"Error fetching next invoice number: {e}")
            raise

    def save_invoice(self, invoice_number, username, total_hours, total_payment, filename):
        sql = """
            INSERT INTO invoices (invoice_number, username, date, total_hours, total_payment, filename)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            self.execute(sql, (invoice_number, username, datetime.now().strftime("%Y-%m-%d"), total_hours, total_payment, filename))
            print("Invoice saved successfully.")
        except Exception as e:
            print(f"Error saving invoice: {e}")
            raise

    def mark_invoice_as_sent(self, invoice_number):
        sql = "UPDATE invoices SET sent = 1 WHERE invoice_number = ?"
        try:
            rows_updated = self.execute(sql, (invoice_number,))
            if rows_updated == 0:
                print("No invoice found to update.")
            else:
                print("Invoice marked as sent successfully.")
        except Exception as e:
            print(f"Error marking invoice as sent: {e}")
            raise

    def __del__(self):
        self.connection.close()
