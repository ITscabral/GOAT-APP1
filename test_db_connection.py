from db_handler import Database

# Initialize database connection
try:
    db = Database()  # Adjust path if needed
    print("Database connection successful.")
    
    # Test a direct query for a known user
    username = 'Lucas Cabral'  # Adjust username to match your data
    password = '123'
    
    # Normalize username by removing spaces and converting to lowercase
    normalized_username = username.lower().replace(" ", "")
    
    # Execute query to test login credentials
    user = db.query(
        "SELECT role FROM users WHERE LOWER(REPLACE(username, ' ', '')) = ? AND password = ?",
        (normalized_username, password)
    )
    
    # Check the query result
    if user:
        print(f"User found: {user}")
    else:
        print("No matching user found. Check database entries and credentials.")
except Exception as e:
    print(f"Error: {e}")
