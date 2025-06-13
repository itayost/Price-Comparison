import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from .models import Base

# Determine which database to use
USE_ORACLE = os.getenv("USE_ORACLE", "false").lower() == "true"

if USE_ORACLE:
    print("Using Oracle Autonomous Database")
    from .oracle_config import OracleConfig

    # Setup Oracle wallet
    try:
        OracleConfig.setup_wallet()
        # Set TNS_ADMIN for thin mode
        wallet_dir = os.getenv('ORACLE_WALLET_DIR', './wallet')
        os.environ['TNS_ADMIN'] = wallet_dir

        # Disable thick mode to ensure we use thin mode
        import oracledb
        oracledb.init_oracle_client = lambda **kwargs: None

        # Use a dummy URL since we're using a creator function
        DATABASE_URL = "oracle+oracledb://"
    except Exception as e:
        print(f"Error setting up Oracle: {str(e)}")
        print("Falling back to PostgreSQL")
        USE_ORACLE = False

if not USE_ORACLE:
    # Original PostgreSQL configuration
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Handle Railway's postgres:// URL format
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    # Fallback for local development
    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///./users.db"
        print("WARNING: No DATABASE_URL found, using SQLite for development")

print(f"Database type: {'Oracle' if USE_ORACLE else 'PostgreSQL/SQLite'}")

# Create engine with appropriate settings
if USE_ORACLE:
    # Oracle specific settings
    # Create custom connection function that matches what worked in debug
    def oracle_connect():
        import oracledb

        wallet_dir = os.path.abspath(os.getenv('ORACLE_WALLET_DIR', './wallet'))
        username = os.getenv('ORACLE_USER', 'ADMIN')
        password = os.getenv('ORACLE_PASSWORD')
        service = os.getenv('ORACLE_SERVICE', 'champdb_low')
        wallet_password = os.getenv('ORACLE_WALLET_PASSWORD')

        # Ensure thin mode
        oracledb.init_oracle_client = lambda **kwargs: None

        # Create connection exactly as in the debug script that worked
        return oracledb.connect(
            user=username,
            password=password,
            dsn=service,
            config_dir=wallet_dir,
            wallet_location=wallet_dir,
            wallet_password=wallet_password
        )

    # Create engine with custom creator
    engine = create_engine(
        "oracle+oracledb://",
        creator=oracle_connect,
        pool_pre_ping=True,
        pool_size=2,  # Start small for Oracle
        max_overflow=3,
        pool_timeout=30,
        pool_recycle=1800,
        echo=False,  # Set to True for debugging
        # Oracle-specific settings to avoid the decimal detection issue
        connect_args={
            "encoding": "UTF-8",
            "nencoding": "UTF-8"
        }
    )
elif "postgresql" in DATABASE_URL:
    # PostgreSQL settings
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800
    )
else:
    # SQLite settings
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    try:
        print("Creating database tables...")
        # For Oracle, we need to handle foreign key constraints carefully
        if USE_ORACLE:
            # Create tables without foreign keys first
            from .models import Base, User, Store

            # Create independent tables first
            User.__table__.create(bind=engine, checkfirst=True)
            Store.__table__.create(bind=engine, checkfirst=True)

            # Then create dependent tables
            Base.metadata.create_all(bind=engine)
        else:
            # For PostgreSQL/SQLite, normal creation works
            Base.metadata.create_all(bind=engine)

        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {str(e)}")
        raise

@contextmanager
def get_db():
    """Database session context manager"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_db_session() -> Session:
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
