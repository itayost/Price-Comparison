#!/usr/bin/env python3
# debug_shufersal_final.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db
from database.new_models import Chain, Branch
from parsers import get_parser
import logging

logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG for more info
logger = logging.getLogger(__name__)

def check_database_state():
    """Check current database state"""
    logger.info("=== Database State ===")
    
    with get_db() as db:
        # Check Shufersal branches
        chain = db.query(Chain).filter(Chain.name == 'shufersal').first()
        if not chain:
            logger.error("❌ Shufersal chain not found!")
            return
        
        logger.info(f"✅ Shufersal chain found: ID={chain.chain_id}")
        
        # Get sample branches
        branches = db.query(Branch).filter(Branch.chain_id == chain.chain_id).limit(10).all()
        logger.info(f"\nShufersal branches in DB: {len(branches)}")
        for branch in branches[:5]:
            logger.info(f"  Branch: store_id='{branch.store_id}', name='{branch.name}'")

def test_parser_output():
    """Test what the parser returns"""
    logger.info("\n=== Parser Output Test ===")
    
    parser = get_parser('shufersal')
    
    # Test store parsing
    store_urls = parser.get_store_file_urls()
    if store_urls:
        logger.info("Testing store file parsing...")
        content = parser.download_gz_file(store_urls[0])
        if content:
            stores = parser.parse_store_data(content)
            logger.info(f"Parsed {len(stores)} stores")
            for store in stores[:3]:
                logger.info(f"  Store: {store}")
    
    # Test price parsing
    price_urls = parser.get_price_file_urls()
    if price_urls:
        logger.info("\nTesting price file parsing...")
        content = parser.download_gz_file(price_urls[0])
        if content:
            prices = parser.parse_price_data(content)
            logger.info(f"Parsed {len(prices)} prices")
            # Get unique store IDs
            store_ids = list(set(p['store_id'] for p in prices))[:5]
            logger.info(f"Unique store IDs in prices: {store_ids}")

def test_import_logic():
    """Test the import logic step by step"""
    logger.info("\n=== Testing Import Logic ===")
    
    parser = get_parser('shufersal')
    
    # Get one price file
    price_urls = parser.get_price_file_urls()
    if not price_urls:
        logger.error("No price files found")
        return
    
    # Download and parse
    content = parser.download_gz_file(price_urls[0])
    if not content:
        logger.error("Failed to download price file")
        return
    
    prices = parser.parse_price_data(content)
    if not prices:
        logger.error("No prices parsed")
        return
    
    # Check branch mapping
    with get_db() as db:
        chain = db.query(Chain).filter(Chain.name == 'shufersal').first()
        if not chain:
            logger.error("Chain not found")
            return
        
        # Get branch mappings
        branches = db.query(Branch).filter(Branch.chain_id == chain.chain_id).all()
        branch_mapping = {b.store_id: b.branch_id for b in branches}
        
        logger.info(f"\nBranch mapping has {len(branch_mapping)} entries")
        logger.info(f"Sample mappings: {dict(list(branch_mapping.items())[:5])}")
        
        # Check if price store IDs match
        matched = 0
        unmatched = []
        for price in prices[:100]:  # Check first 100
            if price['store_id'] in branch_mapping:
                matched += 1
            else:
                if price['store_id'] not in unmatched:
                    unmatched.append(price['store_id'])
        
        logger.info(f"\nMatching results:")
        logger.info(f"  Matched: {matched}/100")
        logger.info(f"  Unmatched store IDs: {unmatched[:10]}")
        
        if unmatched:
            logger.info("\n❌ This is the problem - store IDs don't match!")
            logger.info("Price file store IDs not found in branches table")

if __name__ == "__main__":
    check_database_state()
    test_parser_output()
    test_import_logic()
