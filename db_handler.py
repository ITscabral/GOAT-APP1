# db_handler.py
import sqlite3
import os

class Database:
    def __init__(self, db_path="C:\\Users\\Lucas Cabral\\PycharmProjects\\Python Mini Curso\\GOAT APP\\timesheet.db"):
        # Ensure the database file path is correct
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
            self.cursor.execute(sql, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"SQL Query Error: {e}")
            return []

    def execute(self, sql, params=()):
        try:
            self.cursor.execute(sql, params)
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"SQL Execution Error: {e}")
