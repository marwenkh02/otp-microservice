# backend/test_db.py
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Testing connection to: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL, echo=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        print(f"PostgreSQL version: {result.fetchone()[0]}")
        
        # Check if users table exists
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'users'
        """))
        tables = result.fetchall()
        print(f"Users table exists: {len(tables) > 0}")
        
        # Count users
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        count = result.fetchone()[0]
        print(f"Number of users in database: {count}")
        
except Exception as e:
    print(f"Database connection error: {e}")