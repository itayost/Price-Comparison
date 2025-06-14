#!/usr/bin/env python3
"""
Test Oracle table creation and basic operations
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import engine, init_db, get_db
from database.models import Base, User, Store, Price, Cart, CartItem, create_sample_data
from sqlalchemy import text, inspect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_tables():
    """Check which tables exist"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    logger.info(f"Existing tables: {existing_tables}")
    return existing_tables

def drop_all_tables():
    """Drop all tables (be careful!)"""
    logger.warning("Dropping all tables...")
    try:
        # Drop in reverse order to handle foreign keys
        Base.metadata.drop_all(bind=engine)
        logger.info("✅ All tables dropped")
    except Exception as e:
        logger.error(f"❌ Error dropping tables: {str(e)}")

def create_tables():
    """Create all tables"""
    logger.info("Creating tables...")
    try:
        init_db()
        logger.info("✅ Tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating tables: {str(e)}")
        raise

def test_basic_operations():
    """Test basic CRUD operations"""
    logger.info("Testing basic operations...")

    with get_db() as db:
        try:
            # Test User creation
            logger.info("Creating test user...")
            user = User(email="oracle_test@example.com", password="test_hash")
            db.add(user)
            db.commit()

            # Query user
            found_user = db.query(User).filter(User.email == "oracle_test@example.com").first()
            if found_user:
                logger.info(f"✅ User created and found: {found_user.email}")
            else:
                logger.error("❌ User not found")

            # Test Store creation
            logger.info("Creating test store...")
            store = Store(
                snif_key="TEST-001",
                chain="test_chain",
                city="Test City",
                store_name="Test Store"
            )
            db.add(store)
            db.commit()

            # Test Price creation
            logger.info("Creating test price...")
            price = Price(
                store_id=store.id,
                item_code="TEST001",
                item_name="Test Product טסט",
                item_price=99.99
            )
            db.add(price)
            db.commit()

            # Query to verify
            price_count = db.query(Price).count()
            logger.info(f"✅ Price count: {price_count}")

            # Test Hebrew text
            hebrew_price = Price(
                store_id=store.id,
                item_code="HEB001",
                item_name="חלב תנובה 3% שומן",
                item_price=6.90
            )
            db.add(hebrew_price)
            db.commit()

            # Query Hebrew text
            hebrew_found = db.query(Price).filter(Price.item_name.like('%חלב%')).first()
            if hebrew_found:
                logger.info(f"✅ Hebrew text stored and retrieved: {hebrew_found.item_name}")

            # Cleanup
            logger.info("Cleaning up test data...")
            db.query(Price).delete()
            db.query(Store).delete()
            db.query(User).filter(User.email == "oracle_test@example.com").delete()
            db.commit()

            logger.info("✅ All basic operations passed!")

        except Exception as e:
            logger.error(f"❌ Error in basic operations: {str(e)}")
            db.rollback()
            raise

def main():
    logger.info("Oracle Table Test Script")
    logger.info("=" * 50)

    # Check existing tables
    existing = check_tables()

    if existing:
        logger.info(f"Found {len(existing)} existing tables")
        response = input("Drop existing tables and recreate? (yes/no): ").lower()
        if response == 'yes':
            drop_all_tables()
        else:
            logger.info("Keeping existing tables")
            return

    # Create tables
    create_tables()

    # Verify tables were created
    tables = check_tables()
    expected_tables = ['users', 'stores', 'carts', 'cart_items', 'prices']

    missing = set(expected_tables) - set(tables)
    if missing:
        logger.error(f"❌ Missing tables: {missing}")
    else:
        logger.info("✅ All expected tables created")

    # Test basic operations
    test_basic_operations()

    # Optional: Create sample data
    response = input("\nCreate sample data? (yes/no): ").lower()
    if response == 'yes':
        with get_db() as db:
            create_sample_data(db)

if __name__ == "__main__":
    main()
