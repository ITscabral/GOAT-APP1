import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name='timesheet.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.setup_database()

    def setup_database(self):
        """Set up the required tables."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT,
                phone_number TEXT,
                reset_token TEXT,
                first_login INTEGER DEFAULT 1
            )''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                date TEXT,
                start_time TEXT,
                end_time TEXT
            )''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number INTEGER,
                username TEXT,
                date TEXT,
                total_hours REAL,
                total_payment REAL,
                filename TEXT
            )''')
        self.conn.commit()

    def query(self, query, params=()):
        """Execute a SELECT query."""
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def execute(self, query, params=()):
        """Execute an INSERT/UPDATE/DELETE query."""
        self.cursor.execute(query, params)
        self.conn.commit()

    def get_next_invoice_number(self):
        """Get the next invoice number."""
        result = self.query("SELECT MAX(invoice_number) FROM invoices")
        return (result[0][0] or 0) + 1

    def save_invoice(self, invoice_number, username, total_hours, total_payment, filename):
        """Save the generated invoice in the database."""
        date = datetime.now().strftime('%Y-%m-%d')
        self.execute(
            "INSERT INTO invoices (invoice_number, username, date, total_hours, total_payment, filename) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (invoice_number, username, date, total_hours, total_payment, filename)
        )

    def add_default_users(self):
        """Add default users for testing."""
        self.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', '123', 'admin'))
        self.execute("INSERT OR IGNORE INTO users (username, password, role, first_login) VALUES (?, ?, ?, ?)", ('employee1', '123', 'employee', 1))
        self.execute("INSERT OR IGNORE INTO users (username, password, role, first_login) VALUES (?, ?, ?, ?)", ('employee2', '123', 'employee', 1))
        self.execute("INSERT OR IGNORE INTO users (username, password, role, first_login) VALUES (?, ?, ?, ?)", ('employee3', '123', 'employee', 1))

    def update_password(self, username, new_password):
        """Update password for a user and set first_login to 0."""
        self.execute("UPDATE users SET password = ?, first_login = 0 WHERE username = ?", (new_password, username))

    def is_first_login(self, username):
        """Check if the user is logging in for the first time."""
        result = self.query("SELECT first_login FROM users WHERE username = ?", (username,))
        return result[0][0] == 1 if result else False

    def close(self):
        self.conn.close()

# Run setup if executed directly
if __name__ == "__main__":
    db = Database()
    db.add_default_users()
    db.close()