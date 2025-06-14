import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from .models import Base
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine which database to use
USE_ORACLE = os.getenv("USE_ORACLE", "false").lower() == "true"

if USE_ORACLE:
    logger.info("Using Oracle Autonomous Database")
    import oracledb

    # Ensure we're using thin mode
    oracledb.init_oracle_client = lambda **kwargs: None

    # Create connection function
    def oracle_creator():
        """Create Oracle connection with proper parameters"""
        wallet_dir = os.path.abspath(os.getenv('ORACLE_WALLET_DIR', './wallet'))
        username = os.getenv('ORACLE_USER', 'ADMIN')
        password = os.getenv('ORACLE_PASSWORD')
        service = os.getenv('ORACLE_SERVICE', 'champdb_low')
        wallet_password = os.getenv('ORACLE_WALLET_PASSWORD')

        # Set TNS_ADMIN
        os.environ['TNS_ADMIN'] = wallet_dir

        if not password:
            raise Exception("ORACLE_PASSWORD environment variable not set")
        if not wallet_password:
            raise Exception("ORACLE_WALLET_PASSWORD environment variable not set")

        logger.info(f"Connecting to Oracle service: {service}")

        try:
            conn = oracledb.connect(
                user=username,
                password=password,
                dsn=service,
                config_dir=wallet_dir,
                wallet_location=wallet_dir,
                wallet_password=wallet_password
            )

            # Set session parameters for better performance
            cursor = conn.cursor()
            cursor.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS'")
            cursor.close()

            return conn

        except Exception as e:
            logger.error(f"Oracle connection failed: {str(e)}")
            raise

    # Create engine with Oracle-specific settings
    engine = create_engine(
        "oracle+oracledb://",
        creator=oracle_creator,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        # Oracle-specific settings
        coerce_to_decimal=False,  # Avoid decimal issues
        arraysize=100,  # Optimize fetch size
    )

else:
    # PostgreSQL/SQLite configuration
    DATABASE_URL = os.getenv("DATABASE_URL")

    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///./users.db"
        logger.warning("No DATABASE_URL found, using SQLite for development")

    logger.info(f"Using database: {DATABASE_URL.split('@')[0]}")

    if "postgresql" in DATABASE_URL:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true"
        )
    else:
        # SQLite
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            echo=os.getenv("SQL_ECHO", "false").lower() == "true"
        )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables with proper error handling"""
    try:
        logger.info("Initializing database tables...")

        if USE_ORACLE:
            # For Oracle, create tables in specific order to handle constraints
            from .models import User, Store, Cart, CartItem, Price

            # Drop existing tables if needed (be careful in production!)
            if os.getenv("DROP_TABLES", "false").lower() == "true":
                logger.warning("Dropping existing tables...")
                Base.metadata.drop_all(bind=engine)

            # Create sequences first (Oracle specific)
            with engine.connect() as conn:
                sequences = ['user_id_seq', 'store_id_seq', 'cart_id_seq', 'cart_item_id_seq', 'price_id_seq']
                for seq in sequences:
                    try:
                        conn.execute(text(f"CREATE SEQUENCE {seq}"))
                        logger.info(f"Created sequence: {seq}")
                    except Exception as e:
                        if "ORA-00955" in str(e):  # Sequence already exists
                            logger.info(f"Sequence {seq} already exists")
                        else:
                            logger.error(f"Error creating sequence {seq}: {str(e)}")
                conn.commit()

            # Create tables in order
            logger.info("Creating User table...")
            User.__table__.create(bind=engine, checkfirst=True)

            logger.info("Creating Store table...")
            Store.__table__.create(bind=engine, checkfirst=True)

            logger.info("Creating Cart table...")
            Cart.__table__.create(bind=engine, checkfirst=True)

            logger.info("Creating CartItem table...")
            CartItem.__table__.create(bind=engine, checkfirst=True)

            logger.info("Creating Price table...")
            Price.__table__.create(bind=engine, checkfirst=True)

        else:
            # For PostgreSQL/SQLite, use normal creation
            Base.metadata.create_all(bind=engine)

        logger.info("✅ Database tables initialized successfully!")

        # Test connection
        with engine.connect() as conn:
            if USE_ORACLE:
                result = conn.execute(text("SELECT 1 FROM DUAL"))
            else:
                result = conn.execute(text("SELECT 1"))
            logger.info(f"✅ Database connection test passed: {result.scalar()}")

    except Exception as e:
        logger.error(f"❌ Error initializing database: {str(e)}")
        raise

@contextmanager
def get_db():
    """Database session context manager with error handling"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def get_db_session() -> Session:
    """Get database session for FastAPI dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Add event listener for Oracle session optimization
if USE_ORACLE:
    @event.listens_for(engine, "connect")
    def set_oracle_session_params(dbapi_conn, connection_record):
        """Set Oracle session parameters for better performance"""
        cursor = dbapi_conn.cursor()
        cursor.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS'")
        cursor.execute("ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF'")
        cursor.close()
