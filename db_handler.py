import sqlite3
import os

class Database:
    def __init__(self, db_path=None):
        # Define path and initialize database connection
        db_path = db_path or os.getenv("DATABASE_PATH", "timesheet.db")
        print(f"[DEBUG] Attempting to connect to database at: {db_path}")

        if not os.path.exists(db_path):
            print(f"[DEBUG] Database file '{db_path}' not found. Initializing new database.")
            self.initialize_database(db_path)

        try:
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.cursor = self.connection.cursor()
            print("[DEBUG] Connected to SQLite database successfully.")
        except sqlite3.Error as e:
            print(f"[ERROR] Database connection error: {e}")

    def initialize_database(self, db_path):
        """Initialize the SQLite database and create tables."""
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.connection.cursor()
        print("[DEBUG] Creating tables in new database...")

        # Create tables
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            phone_number TEXT
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS time_entries (
            username TEXT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            FOREIGN KEY (username) REFERENCES users (username)
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS invoices (
            invoice_number INTEGER PRIMARY KEY,
            username TEXT,
            date TEXT,
            total_hours REAL,
            total_payment REAL,
            filename TEXT,
            FOREIGN KEY (username) REFERENCES users (username)
        )''')
       

    def query(self, sql, params=()):
        try:
            print(f"[DEBUG] Executing SQL Query: {sql} with params: {params}")
            self.cursor.execute(sql, params)
            result = self.cursor.fetchall()
            print(f"[DEBUG] Query result: {result}")
            return result
        except sqlite3.Error as e:
            print(f"[ERROR] SQL Query Error: {e}")
            return []

    def execute(self, sql, params=()):
        try:
            print(f"[DEBUG] Executing SQL Command: {sql} with params: {params}")
            self.cursor.execute(sql, params)
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"[ERROR] SQL Execution Error: {e}")
