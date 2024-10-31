from db_handler import Database

# Create an instance of Database
try:
    db = Database()
    print("Database connection successful.")
except Exception as e:
    print(f"Error connecting to database: {e}")
