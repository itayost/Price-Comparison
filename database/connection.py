# price_comparison_server/database/connection.py

import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import models (without Product)
from .new_models import Base, User, Chain, Branch, ChainProduct, BranchPrice, SavedCart

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
USE_ORACLE = os.getenv("USE_ORACLE", "false").lower() == "true"

# For Oracle with wallet
TNS_ADMIN = os.getenv("TNS_ADMIN") or os.getenv("ORACLE_WALLET_DIR", "./wallet")

if USE_ORACLE:
    # Oracle configuration
    wallet_dir = Path(TNS_ADMIN).resolve()
    os.environ['TNS_ADMIN'] = str(wallet_dir)

    # Build Oracle connection string
    ORACLE_USER = os.getenv("ORACLE_USER")
    ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")
    # Check for both ORACLE_DSN and ORACLE_SERVICE (for compatibility)
    ORACLE_DSN = os.getenv("ORACLE_DSN") or os.getenv("ORACLE_SERVICE", "champdb_low")

    # Include wallet configuration in connection
    connect_args = {
        "config_dir": str(wallet_dir),
        "wallet_location": str(wallet_dir)
    }

    # Add wallet password if provided
    wallet_password = os.getenv("ORACLE_WALLET_PASSWORD")
    if wallet_password:
        connect_args["wallet_password"] = wallet_password

    DATABASE_URL = f"oracle+oracledb://{ORACLE_USER}:{ORACLE_PASSWORD}@{ORACLE_DSN}"

    logger.info(f"Using Oracle database with TNS_ADMIN: {wallet_dir}")
    logger.info(f"Connecting to DSN: {ORACLE_DSN}")
else:
    # SQLite/PostgreSQL configuration
    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///./price_comparison.db"
    logger.info(f"Using database: {DATABASE_URL}")

# Create engine
try:
    if USE_ORACLE:
        # Oracle-specific engine configuration with wallet
        from pathlib import Path
        wallet_dir = Path(TNS_ADMIN).resolve()

        engine = create_engine(
            DATABASE_URL,
            poolclass=NullPool,  # Disable pooling for Oracle
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            connect_args={
                "config_dir": str(wallet_dir),
                "wallet_location": str(wallet_dir),
                "wallet_password": os.getenv("ORACLE_WALLET_PASSWORD")
            }
        )
    else:
        # SQLite/PostgreSQL engine
        engine = create_engine(
            DATABASE_URL,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
        )

    # Test connection
    with engine.connect() as conn:
        if USE_ORACLE:
            result = conn.execute(text("SELECT 1 FROM DUAL"))
        else:
            result = conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful!")

except Exception as e:
    logger.error(f"❌ Database connection failed: {str(e)}")
    if USE_ORACLE:
        logger.error(f"TNS_ADMIN is set to: {os.environ.get('TNS_ADMIN')}")
        logger.error("Make sure wallet files are in the correct location")
    raise

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get database session with automatic cleanup"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session():
    """FastAPI dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    try:
        logger.info("Initializing database tables...")

        if USE_ORACLE:
            logger.info("Using Oracle database...")

            # Drop tables if requested (careful!)
            if os.getenv("DROP_TABLES", "false").lower() == "true":
                logger.warning("Dropping existing tables...")
                Base.metadata.drop_all(bind=engine)

            # Create all tables at once first
            logger.info("Creating all tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Tables created with SQLAlchemy")

            # Then create sequences that might be missing
            with engine.connect() as conn:
                sequences = ['user_id_seq', 'chain_id_seq', 'branch_id_seq',
                           'chain_product_id_seq', 'price_id_seq', 'cart_id_seq']

                for seq in sequences:
                    try:
                        conn.execute(text(f"CREATE SEQUENCE {seq}"))
                        logger.info(f"Created sequence: {seq}")
                    except Exception as e:
                        if "ORA-00955" in str(e):  # Sequence already exists
                            logger.debug(f"Sequence {seq} already exists")
                        else:
                            logger.warning(f"Could not create sequence {seq}: {e}")
                conn.commit()

            # Verify tables were created
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM user_tables WHERE table_name IN ('CHAINS', 'BRANCHES', 'USERS')"))
                count = result.scalar()
                if count > 0:
                    logger.info(f"✅ Verified {count} tables exist in Oracle")
                else:
                    logger.error("❌ No tables found after creation!")
        else:
            # For PostgreSQL/SQLite, use normal creation
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Tables created for non-Oracle database")

        logger.info("✅ Database tables initialized successfully!")

        # Seed initial data
        with get_db() as db:
            seed_chains(db)

    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def seed_chains(db: Session):
    """Seed initial chain data if not exists"""
    try:
        chains = [
            Chain(name='shufersal', display_name='שופרסל'),
            Chain(name='victory', display_name='ויקטורי')
        ]

        for chain in chains:
            existing = db.query(Chain).filter_by(name=chain.name).first()
            if not existing:
                db.add(chain)
                logger.info(f"Added chain: {chain.name}")

        db.commit()
        logger.info("✅ Initial chain data seeded!")

    except Exception as e:
        logger.error(f"Error seeding chains: {str(e)}")
        db.rollback()


# Only initialize when run directly
if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialization complete!")
