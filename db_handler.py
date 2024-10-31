import sqlite3
import os


class Database:
    def __init__(self, db_path="C:\\Users\\Lucas Cabral\\PycharmProjects\\Python Mini Curso\\GOAT APP\\timesheet.db"):
        print(f"Attempting to connect to database at: {db_path}")
        if not os.path.exists(db_path):
            print(f"Database file '{db_path}' not found.")
            raise FileNotFoundError("The specified database file does not exist.")
        # Establish connection
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.connection.cursor()
        print("Connected to SQLite database successfully.")

    def query(self, sql, params=()):
        try:
            print(f"Executing SQL Query: {sql} with params: {params}")  # Detailed debug info
            self.cursor.execute(sql, params)
            result = self.cursor.fetchall()
            print(f"Query result: {result}")  # Show fetched results
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
