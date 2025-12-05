from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os
from dotenv import load_dotenv
import sys
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

# Load .env file from backend directory
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Get DATABASE_URL from .env
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/otp_project")

# Debug: Print the connection string (mask password for security)
print("=" * 60)
print("DATABASE CONNECTION DEBUG")
print("=" * 60)
print(f"Loaded DATABASE_URL from .env: {DATABASE_URL}")
print(f".env file location: {env_path}")
print(f".env exists: {env_path.exists()}")
print("=" * 60)

# Ensure we're using PostgreSQL
if DATABASE_URL and "sqlite" in DATABASE_URL.lower():
    print("ERROR: SQLite detected! Should be PostgreSQL")
    sys.exit(1)

# Store original for parsing before normalization
_original_url = DATABASE_URL

# Normalize connection string format (postgresql+psycopg2:// -> postgresql://)
# SQLAlchemy handles both, but we normalize for consistency
if DATABASE_URL and DATABASE_URL.startswith("postgresql+psycopg2://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://", 1)
    print("Note: Normalized connection string from postgresql+psycopg2:// to postgresql://")

# Extract components from DATABASE_URL for logging
try:
    # Parse DATABASE_URL: postgresql://user:password@host:port/dbname
    # Use original URL for parsing to handle postgresql+psycopg2:// format
    parse_url = _original_url or DATABASE_URL
    if '@' in parse_url:
        parts = parse_url.split('@')
        # Handle both postgresql:// and postgresql+psycopg2://
        protocol_part = parts[0]
        if '://' in protocol_part:
            user_pass = protocol_part.split('://')[1]
        elif '+psycopg2://' in protocol_part:
            user_pass = protocol_part.split('+psycopg2://')[1]
        else:
            user_pass = protocol_part
        if ':' in user_pass:
            DB_USER = user_pass.split(':')[0]
            DB_PASSWORD = user_pass.split(':')[1]
        else:
            DB_USER = user_pass
            DB_PASSWORD = "****"
        
        host_db = parts[1]
        if '/' in host_db:
            host_port = host_db.split('/')[0]
            DB_NAME = host_db.split('/')[1]
            if ':' in host_port:
                DB_HOST = host_port.split(':')[0]
                DB_PORT = host_port.split(':')[1]
            else:
                DB_HOST = host_port
                DB_PORT = "5432"
        else:
            DB_HOST = host_db
            DB_PORT = "5432"
            DB_NAME = "unknown"
    else:
        DB_USER = "unknown"
        DB_PASSWORD = "****"
        DB_HOST = "unknown"
        DB_PORT = "unknown"
        DB_NAME = "unknown"
except Exception:
    # If parsing fails, use defaults
    DB_USER = "unknown"
    DB_PASSWORD = "****"
    DB_HOST = "unknown"
    DB_PORT = "unknown"
    DB_NAME = "unknown"

# Mask password in connection string for logging
_log_url = DATABASE_URL.replace(f":{DB_PASSWORD}", ":****") if DB_PASSWORD != "****" else DATABASE_URL

# Log connection info (masked password)
print("=" * 60)
print("DATABASE CONNECTION INFO")
print("=" * 60)
print(f"Connection string: {_log_url}")
print(f"Database user: {DB_USER}")
print(f"Database name: {DB_NAME}")
print(f"Host: {DB_HOST}:{DB_PORT}")
print(f".env file location: {env_path} ({'found' if env_path.exists() else 'not found'})")
print("=" * 60)

# Create ONE global engine instance
engine = create_engine(
    DATABASE_URL,
    echo=True,  # This will show ALL SQL queries
    pool_pre_ping=True,
    pool_recycle=3600
)

# Create ONE session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

Base = declarative_base()
# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Get database session - FastAPI dependency
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Explicit commit
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# Context manager for manual session management
@contextmanager
def get_db_context():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# Initialize database tables
def init_db():
    """Create all tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

# Test connection
def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT version();")
            print(f"Connected to: {result.fetchone()[0]}")
        return True
    except Exception as e:
        print(f"Connection error: {e}")
        return False