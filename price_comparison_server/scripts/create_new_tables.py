# price_comparison_server/scripts/create_new_tables.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix Oracle connection by setting config_dir
def fix_oracle_creator():
    """Create Oracle connection with proper config_dir"""
    import oracledb
    
    wallet_dir = os.path.abspath(os.getenv('ORACLE_WALLET_DIR', './wallet'))
    username = os.getenv('ORACLE_USER', 'ADMIN')
    password = os.getenv('ORACLE_PASSWORD')
    service = os.getenv('ORACLE_SERVICE', 'champdb_low')
    wallet_password = os.getenv('ORACLE_WALLET_PASSWORD')
    
    # Set TNS_ADMIN
    os.environ['TNS_ADMIN'] = wallet_dir
    
    return oracledb.connect(
        user=username,
        password=password,
        dsn=service,
        config_dir=wallet_dir,  # This is the key fix!
        wallet_location=wallet_dir,
        wallet_password=wallet_password
    )

# Monkey patch the connection before importing
if os.getenv("USE_ORACLE", "false").lower() == "true":
    from database import connection
    connection.oracle_creator = fix_oracle_creator

from database.connection import engine, get_db
from database.new_models import (
    Base, Chain, Branch, Product, ChainProduct, 
    BranchPrice, ProductMatchingRule, PriceHistory,
    create_all_tables, seed_initial_data
)
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_existing_tables(engine):
    """Check which tables already exist"""
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    new_tables = ['chains', 'branches', 'products', 'chain_products', 
                  'branch_prices', 'product_matching_rules', 'price_history']
    
    existing = [table for table in new_tables if table.lower() in [t.lower() for t in existing_tables]]
    missing = [table for table in new_tables if table.lower() not in [t.lower() for t in existing_tables]]
    
    return existing, missing


def create_tables_with_verification():
    """Create new tables with verification"""
    try:
        logger.info("🔍 Checking existing tables...")
        existing, missing = check_existing_tables(engine)
        
        if existing:
            logger.warning(f"⚠️ Found existing tables: {existing}")
            response = input("Do you want to DROP existing tables and recreate? (yes/no): ")
            
            if response.lower() == 'yes':
                logger.info("Dropping existing tables...")
                # Drop in reverse order to handle foreign keys
                with engine.begin() as conn:
                    # For Oracle, we need to handle this differently
                    if os.getenv("USE_ORACLE", "false").lower() == "true":
                        for table in ['price_history', 'branch_prices', 'chain_products', 
                                     'products', 'branches', 'chains', 'product_matching_rules']:
                            try:
                                # Try to drop table, ignore if doesn't exist
                                conn.execute(text(f'DROP TABLE {table.upper()} CASCADE CONSTRAINTS'))
                                logger.info(f"Dropped table: {table}")
                            except Exception as e:
                                if "ORA-00942" not in str(e):  # Table doesn't exist
                                    logger.warning(f"Could not drop {table}: {e}")
                    else:
                        for table in ['price_history', 'branch_prices', 'chain_products', 
                                     'products', 'branches', 'chains', 'product_matching_rules']:
                            try:
                                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                            except Exception as e:
                                logger.error(f"Error dropping {table}: {e}")
            else:
                logger.info("Keeping existing tables.")
                return
        
        logger.info("📦 Creating new tables...")
        create_all_tables(engine)
        
        # Verify creation
        existing, missing = check_existing_tables(engine)
        
        if missing:
            logger.error(f"❌ Failed to create tables: {missing}")
            return False
        
        logger.info("✅ All tables created successfully!")
        
        # Seed initial data
        logger.info("🌱 Seeding initial data...")
        with get_db() as db:
            seed_initial_data(db)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {str(e)}")
        return False


def display_table_info():
    """Display information about created tables"""
    try:
        with engine.begin() as conn:
            # For Oracle, we need different queries
            if os.getenv("USE_ORACLE", "false").lower() == "true":
                # Count tables
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM user_tables 
                    WHERE table_name IN ('CHAINS', 'BRANCHES', 'PRODUCTS', 
                                        'CHAIN_PRODUCTS', 'BRANCH_PRICES')
                    ORDER BY table_name
                """))
            else:
                # PostgreSQL/SQLite query
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('chains', 'branches', 'products', 
                                      'chain_products', 'branch_prices')
                    ORDER BY table_name
                """))
            
            tables = [row[0] for row in result]
            
            logger.info("\n📊 Database Schema Summary:")
            logger.info(f"Total tables created: {len(tables)}")
            for table in tables:
                logger.info(f"  ✓ {table}")
            
            # Check chain data
            result = conn.execute(text("SELECT COUNT(*) FROM chains"))
            chain_count = result.scalar()
            logger.info(f"\n🏪 Chains in database: {chain_count}")
            
            if chain_count > 0:
                result = conn.execute(text("SELECT name, display_name FROM chains"))
                for name, display in result:
                    logger.info(f"  • {name}: {display}")
    
    except Exception as e:
        logger.error(f"Error displaying table info: {e}")


if __name__ == "__main__":
    logger.info("=== Creating New Database Schema ===")
    
    if create_tables_with_verification():
        display_table_info()
        logger.info("\n✅ Database schema is ready!")
        logger.info("Next steps:")
        logger.info("1. Run store data parser to populate branches")
        logger.info("2. Run price scrapers with new import logic")
    else:
        logger.error("\n❌ Failed to create database schema")