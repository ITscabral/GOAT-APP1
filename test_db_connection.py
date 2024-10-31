# test_db_connection.py
from db_handler import Database

# Create an instance of Database
try:
    db = Database()
    print("Database connection successful.")
    
    # Test login credentials with case- and space-insensitive logic
    username_input = 'Michel Silva'  # Example: Michel Silva, michel silva, etc.
    password_input = '123'

    # Normalize username by converting to lowercase and removing spaces
    normalized_username = username_input.strip().lower().replace(" ", "")
    print(f"Testing login with normalized Username: '{normalized_username}' and Password: '{password_input}'")
    
    # Execute the query with normalization
    user = db.query(
        "SELECT role FROM users WHERE LOWER(REPLACE(username, ' ', '')) = ? AND password = ?",
        (normalized_username, password_input)
    )
    
    # Check and display the query result
    if user:
        print(f"Login successful for '{username_input}' with role: {user[0][0]}")
    else:
        print(f"Login failed for '{username_input}'")

except Exception as e:
    print(f"Error connecting to database: {e}")
