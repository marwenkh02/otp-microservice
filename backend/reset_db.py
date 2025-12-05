#!/usr/bin/env python3
"""
Database Reset Script
This script drops all tables and recreates them, effectively resetting the database.
WARNING: This will delete all data!
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine, SessionLocal, Base
from app.models import User, OTPConfig, OTPEvent, AuditLog, UserSession

def reset_database():
    """Drop all tables and recreate them"""
    print("=" * 60)
    print("DATABASE RESET SCRIPT")
    print("=" * 60)
    print("WARNING: This will delete ALL data from the database!")
    
    # Confirm before proceeding
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        confirm = "yes"
    else:
        confirm = input("Type 'yes' to confirm: ").strip().lower()
    
    if confirm != "yes":
        print("Reset cancelled.")
        return
    
    print("\nConnecting to database...")
    print(f"Database URL: {os.getenv('DATABASE_URL', 'Not set - using constructed URL')}")
    
    try:
        # Drop all tables
        print("\nDropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("✓ All tables dropped successfully")
        
        # Recreate all tables
        print("\nCreating all tables...")
        Base.metadata.create_all(bind=engine)
        print("✓ All tables created successfully")
        
        # Verify tables exist
        print("\nVerifying database structure...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            print(f"✓ Found {len(tables)} tables:")
            for table in tables:
                print(f"  - {table}")
        
        print("\n" + "=" * 60)
        print("Database reset completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nERROR: Failed to reset database: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    reset_database()



