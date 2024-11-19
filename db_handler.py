import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self, db_path="/var/data/timesheet.db"):
        """
        Initialize the database connection and ensure schema updates.

        Args:
            db_path (str): The path to the SQLite database file.
        """
        self.db_path = db_path

        # Check if the database file exists
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file '{db_path}' not found.")

        # Connect to the database and ensure schema is up-to-date
        self.connect_db()
        self.ensure_schema_updates()

    def connect_db(self):
        """Establish a connection to the SQLite database."""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            print(f"Connected to SQLite database at '{self.db_path}'.")
        except sqlite3.Error as e:
            raise ConnectionError(f"Database connection error: {e}")

    def query(self, sql, params=()):
        """
        Execute a SELECT query and return the results.

        Args:
            sql (str): The SQL query string.
            params (tuple): Parameters for the query.

        Returns:
            list: The query results as a list of rows.
        """
        try:
            with self.connection:
                cursor = self.connection.execute(sql, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Query error: {e}")
            return []

    def execute(self, sql, params=()):
        """
        Execute an INSERT, UPDATE, or DELETE query.

        Args:
            sql (str): The SQL query string.
            params (tuple): Parameters for the query.

        Returns:
            int: Number of rows affected.
        """
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
            self.add_column_if_not_exists(
                table="invoices",
                column="sent",
                column_type="INTEGER DEFAULT 0"
            )
        except sqlite3.Error as e:
            print(f"Error ensuring schema updates: {e}")

    def add_column_if_not_exists(self, table, column, column_type):
        """
        Add a column to a table if it does not already exist.

        Args:
            table (str): The name of the table.
            column (str): The name of the column to add.
            column_type (str): The data type of the column.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]
            if column not in columns:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                print(f"Added column '{column}' to table '{table}'.")
                self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error adding column '{column}' to table '{table}': {e}")

    def get_next_invoice_number(self):
        """
        Get the next available invoice number.

        Returns:
            int: The next invoice number.
        """
        try:
            sql = "SELECT COALESCE(MAX(invoice_number), 0) + 1 AS next_id FROM invoices"
            result = self.query(sql)
            return result[0]['next_id'] if result else 1
        except sqlite3.Error as e:
            print(f"Error fetching next invoice number: {e}")
            return 1

    def save_invoice(self, invoice_number, username, total_hours, total_payment, filename):
        """
        Save the invoice details to the invoices table.

        Args:
            invoice_number (int): The invoice number.
            username (str): The username associated with the invoice.
            total_hours (float): The total hours worked.
            total_payment (float): The total payment.
            filename (str): The file name of the invoice.
        """
        try:
            print(f"Saving invoice {invoice_number} for user '{username}'...")
            self.execute(
                """
                INSERT INTO invoices (invoice_number, username, date, total_hours, total_payment, filename, sent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (invoice_number, username, datetime.now().strftime("%Y-%m-%d"), total_hours, total_payment, filename, 0)
            )
            print("Invoice saved successfully.")
        except sqlite3.Error as e:
            print(f"Error saving invoice: {e}")

    def mark_invoice_as_sent(self, invoice_number):
        """
        Mark an invoice as sent.

        Args:
            invoice_number (int): The invoice number to mark as sent.
        """
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
        """Close the database connection when the object is deleted."""
        try:
            if hasattr(self, "connection") and self.connection:
                self.connection.close()
                print("Database connection closed.")
        except AttributeError:
            pass