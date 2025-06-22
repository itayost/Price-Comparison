#!/usr/bin/env python3
# price_comparison_server/scripts/simple_cart_test.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Direct imports to avoid the problematic __init__.py files
from database.connection import get_db
from database.new_models import ChainProduct, Branch
from dataclasses import dataclass
from typing import List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define CartItem here to avoid import issues
@dataclass
class CartItem:
    barcode: str
    quantity: int = 1
    name: Optional[str] = None


def test_simple_cart():
    """Simple test without using the full service"""
    
    with get_db() as db:
        # 1. Check what products we have
        logger.info("=== Checking Database ===")
        
        product_count = db.query(ChainProduct).count()
        logger.info(f"Total products in database: {product_count}")
        
        if product_count == 0:
            logger.error("No products found! Please run import scripts first:")
            logger.error("  python scripts/import_stores.py")
            logger.error("  python scripts/import_prices.py --limit 5")
            return
        
        # 2. Get sample products
        sample_products = db.query(ChainProduct).limit(5).all()
        logger.info("\nSample products:")
        for p in sample_products:
            logger.info(f"  - {p.barcode}: {p.name}")
        
        # 3. Check branches
        branch_count = db.query(Branch).count()
        logger.info(f"\nTotal branches: {branch_count}")
        
        # Get sample cities
        cities = db.query(Branch.city).distinct().limit(5).all()
        logger.info("\nSample cities:")
        for city in cities:
            logger.info(f"  - {city[0]}")
        
        # 4. Simple price check
        if sample_products and cities:
            product = sample_products[0]
            city = cities[0][0]
            
            logger.info(f"\n=== Price Check ===")
            logger.info(f"Product: {product.name} ({product.barcode})")
            logger.info(f"City: {city}")
            
            # Find branches in city
            from sqlalchemy import func
            branches = db.query(Branch).filter(
                func.lower(Branch.city).like(f'%{city.lower()}%')
            ).limit(3).all()
            
            logger.info(f"\nFound {len(branches)} branches in {city}")
            
            for branch in branches:
                # Check if product exists in this branch
                from database.new_models import BranchPrice
                price_info = db.query(BranchPrice).join(ChainProduct).filter(
                    ChainProduct.barcode == product.barcode,
                    ChainProduct.chain_id == branch.chain_id,
                    BranchPrice.branch_id == branch.branch_id
                ).first()
                
                if price_info:
                    logger.info(f"  - {branch.name}: ₪{price_info.price}")
                else:
                    logger.info(f"  - {branch.name}: Not available")


if __name__ == "__main__":
    logger.info("Simple Cart Test - Direct Database Check\n")
    
    try:
        test_simple_cart()
        logger.info("\n✅ Basic database connectivity working!")
        logger.info("\nNext steps:")
        logger.info("1. Fix the import issues in __init__.py files")
        logger.info("2. Install missing dependencies if needed")
        logger.info("3. Run the full cart comparison test")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
