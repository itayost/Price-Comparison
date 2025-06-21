#!/usr/bin/env python3
# price_comparison_server/scripts/check_oracle_tables.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db, engine
from sqlalchemy import text, inspect
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_tables():
    """Check what tables and columns exist in the database"""
    logger.info("Checking database tables and structure...")
    
    inspector = inspect(engine)
    
    # Get all table names
    tables = inspector.get_table_names()
    logger.info(f"\nFound {len(tables)} tables:")
    for table in sorted(tables):
        logger.info(f"  - {table}")
    
    # Check for new tables
    new_tables = ['chains', 'branches', 'products', 'chain_products', 'branch_prices']
    logger.info(f"\nChecking for new schema tables:")
    for table in new_tables:
        exists = table.lower() in [t.lower() for t in tables]
        logger.info(f"  - {table}: {'✓ EXISTS' if exists else '✗ NOT FOUND'}")
    
    # Check specific table structures
    with engine.begin() as conn:
        # Check if we have the old structure (snif_key based)
        if os.getenv("USE_ORACLE", "false").lower() == "true":
            # Oracle query
            result = conn.execute(text("""
                SELECT table_name, column_name 
                FROM user_tab_columns 
                WHERE table_name IN ('PRICES', 'PRODUCTS', 'STORES', 'BRANCHES', 'CHAINS')
                ORDER BY table_name, column_id
            """))
        else:
            # PostgreSQL/SQLite query
            result = conn.execute(text("""
                SELECT table_name, column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name IN ('prices', 'products', 'stores', 'branches', 'chains')
                ORDER BY table_name, ordinal_position
            """))
        
        current_table = None
        for row in result:
            table_name = row[0]
            column_name = row[1]
            
            if current_table != table_name:
                logger.info(f"\n{table_name} columns:")
                current_table = table_name
            
            logger.info(f"  - {column_name}")
    
    # Check for data in key tables
    logger.info("\nChecking data counts:")
    with get_db() as db:
        # Try different table names
        for table_pair in [('prices', 'PRICES'), ('branches', 'BRANCHES'), ('chains', 'CHAINS')]:
            for table_name in table_pair:
                try:
                    result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    logger.info(f"  - {table_name}: {count} rows")
                    break
                except Exception:
                    continue


def check_imported_data():
    """Check what was actually imported"""
    logger.info("\n\nChecking imported store data:")
    
    with get_db() as db:
        # Check if branches table exists and has data
        try:
            result = db.execute(text("""
                SELECT c.name as chain_name, COUNT(b.branch_id) as store_count
                FROM chains c
                LEFT JOIN branches b ON c.chain_id = b.chain_id
                GROUP BY c.name
            """))
            
            logger.info("\nStores per chain:")
            for row in result:
                logger.info(f"  - {row[0]}: {row[1]} stores")
                
        except Exception as e:
            logger.warning(f"Could not query new tables: {e}")
            
        # Check old structure
        try:
            # Check if we have snif_key based data
            result = db.execute(text("SELECT COUNT(DISTINCT snif_key) FROM prices"))
            count = result.scalar()
            logger.info(f"\nOld structure - unique snif_keys in prices: {count}")
        except Exception:
            pass


if __name__ == "__main__":
    check_tables()
    check_imported_data()