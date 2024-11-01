from db_handler import Database

# Instantiate the Database class
try:
    db = Database()
    print("Database connection successful.")

    # Test login credentials, remove spaces, and make lowercase
    username = 'Michel Silva'.replace(" ", "").lower()
    password = '123'
    user = db.query(
        "SELECT role FROM users WHERE LOWER(REPLACE(username, ' ', '')) = ? AND password = ?",
        (username, password)
    )
    
    # Check result and print output
    if user:
        print(f"Login successful for '{username}' with role: {user[0][0]}")
    else:
        print("Invalid credentials or user not found.")
except Exception as e:
    print(f"Error connecting to database: {e}")
