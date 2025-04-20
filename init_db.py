"""
Database initialization script
"""
from models import setup_database

if __name__ == "__main__":
    print("Initializing database...")
    setup_database()
    print("Database initialized successfully!")