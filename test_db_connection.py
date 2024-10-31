# test_db_connection.py
from db_handler import Database

# Create an instance of Database
try:
    db = Database()
    print("Database connection successful.")
    
    # Test login credentials
    username = 'michel_silva'
    password = '123'
    user = db.query("SELECT role FROM users WHERE LOWER(username) = ? AND password = ?", (username.lower(), password))
    print("Query result for test user:", user)
except Exception as e:
    print(f"Error connecting to database: {e}")
