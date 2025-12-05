from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

# Load .env file from backend directory (parent of app directory)
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Also try loading from current directory (for backwards compatibility)
load_dotenv()

# Always use PostgreSQL - never default to SQLite
# If DATABASE_URL is not set, construct it from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

# Store original for parsing before normalization
_original_url = DATABASE_URL

# Normalize connection string format (postgresql+psycopg2:// -> postgresql://)
# SQLAlchemy handles both, but we normalize for consistency
if DATABASE_URL and DATABASE_URL.startswith("postgresql+psycopg2://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://", 1)
    print("Note: Normalized connection string from postgresql+psycopg2:// to postgresql://")

if not DATABASE_URL:
    # Detect if running in Docker (use 'db' hostname) or locally (use 'localhost')
    DB_HOST = os.getenv("DB_HOST")
    if not DB_HOST:
        # Check if we're in Docker by looking for /.dockerenv or DOCKER_CONTAINER env var
        if os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER') == 'true':
            DB_HOST = "db"  # Docker service name
        else:
            DB_HOST = "localhost"  # Local development
    
    DB_USER = os.getenv("POSTGRES_USER", "openpam")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "openpam123")
    DB_NAME = os.getenv("POSTGRES_DB", "openpam")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
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

# Ensure we're using PostgreSQL, not SQLite
if DATABASE_URL.startswith("sqlite"):
    print("ERROR: SQLite database detected! This should not happen.")
    print(f"Current DATABASE_URL: {DATABASE_URL}")
    print("Please set DATABASE_URL or POSTGRES_* environment variables.")
    sys.exit(1)

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

SQLALCHEMY_DATABASE_URL = DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()