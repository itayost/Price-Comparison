# price_comparison_server/scripts/import_chain_data.py

import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import logging
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db
from database.new_models import Chain, Branch, Product, ChainProduct, BranchPrice
from parsers import get_parser, get_all_parsers, PARSER_REGISTRY
from sqlalchemy import func
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ChainDataImporter:
    """Main class for importing chain data"""
    
    def __init__(self):
        self.branch_mappings = {}  # Maps store_id to branch_id for each chain
        
    def import_stores(self, chain_name: str, stores: List[Dict[str, Any]]) -> int:
        """Import stores to database"""
        with get_db() as db:
            try:
                # Get chain
                chain = db.query(Chain).filter(Chain.name == chain_name).first()
                if not chain:
                    logger.error(f"Chain '{chain_name}' not found in database")
                    logger.info(f"Creating chain '{chain_name}'")
                    chain = Chain(name=chain_name, display_name=chain_name.title())
                    db.add(chain)
                    db.flush()
                
                imported = 0
                updated = 0
                
                # Create mapping for this chain
                self.branch_mappings[chain_name] = {}
                
                for store_data in stores:
                    # Check if branch exists
                    existing = db.query(Branch).filter(
                        Branch.chain_id == chain.chain_id,
                        Branch.store_id == store_data['store_id']
                    ).first()
                    
                    if existing:
                        # Update existing branch
                        existing.name = store_data['store_name']
                        existing.address = store_data['address']
                        existing.city = store_data['city']
                        updated += 1
                        self.branch_mappings[chain_name][store_data['store_id']] = existing.branch_id
                    else:
                        # Create new branch
                        branch = Branch(
                            chain_id=chain.chain_id,
                            store_id=store_data['store_id'],
                            name=store_data['store_name'],
                            address=store_data['address'],
                            city=store_data['city']
                        )
                        db.add(branch)
                        db.flush()
                        imported += 1
                        self.branch_mappings[chain_name][store_data['store_id']] = branch.branch_id
                
                db.commit()
                logger.info(f"{chain_name}: Imported {imported} new stores, updated {updated} existing stores")
                return imported + updated
                
            except Exception as e:
                logger.error(f"Error importing stores: {e}")
                db.rollback()
                return 0
    
    def import_prices(self, chain_name: str, prices: List[Dict[str, Any]]) -> int:
        """Import prices to database"""
        with get_db() as db:
            try:
                # Get chain
                chain = db.query(Chain).filter(Chain.name == chain_name).first()
                if not chain:
                    logger.error(f"Chain '{chain_name}' not found")
                    return 0
                
                # Process in batches
                batch_size = 1000
                total_products = 0
                total_prices = 0
                
                for i in range(0, len(prices), batch_size):
                    batch = prices[i:i + batch_size]
                    
                    for price_data in batch:
                        # Get or create chain product
                        chain_product = db.query(ChainProduct).filter(
                            ChainProduct.chain_id == chain.chain_id,
                            ChainProduct.barcode == price_data['barcode']
                        ).first()
                        
                        if not chain_product:
                            # Create new chain product
                            chain_product = ChainProduct(
                                chain_id=chain.chain_id,
                                barcode=price_data['barcode'],
                                name=price_data['name'],
                                product_id=None  # Will be matched later
                            )
                            db.add(chain_product)
                            db.flush()
                            total_products += 1
                        
                        # Get branch_id from mapping
                        branch_id = price_data.get('branch_id')
                        if not branch_id:
                            continue
                        
                        # Update or create price
                        existing_price = db.query(BranchPrice).filter(
                            BranchPrice.chain_product_id == chain_product.chain_product_id,
                            BranchPrice.branch_id == branch_id
                        ).first()
                        
                        if existing_price:
                            existing_price.price = price_data['price']
                            existing_price.last_updated = datetime.utcnow()
                        else:
                            branch_price = BranchPrice(
                                chain_product_id=chain_product.chain_product_id,
                                branch_id=branch_id,
                                price=price_data['price']
                            )
                            db.add(branch_price)
                        
                        total_prices += 1
                    
                    # Commit batch
                    db.commit()
                    logger.info(f"Processed batch {i//batch_size + 1}, total prices: {total_prices}")
                
                logger.info(f"{chain_name}: Created {total_products} new products, processed {total_prices} prices")
                return total_prices
                
            except Exception as e:
                logger.error(f"Error importing prices: {e}")
                db.rollback()
                return 0
    
    def import_chain_data(self, chain_name: str, include_prices: bool = False):
        """Import all data for a specific chain"""
        logger.info(f"\n{'='*50}")
        logger.info(f"Importing data for {chain_name.upper()}")
        logger.info(f"{'='*50}\n")
        
        # Get parser
        parser = get_parser(chain_name)
        
        # Import stores
        logger.info(f"📦 Fetching store data...")
        stores = parser.process_stores()
        
        if stores:
            logger.info(f"Found {len(stores)} stores")
            self.import_stores(chain_name, stores)
        else:
            logger.warning(f"No stores found for {chain_name}")
            return
        
        # Import prices if requested
        if include_prices:
            logger.info(f"\n💰 Fetching price data...")
            prices = parser.process_prices(self.branch_mappings.get(chain_name, {}))
            
            if prices:
                logger.info(f"Found {len(prices)} prices")
                self.import_prices(chain_name, prices)
            else:
                logger.warning(f"No prices found for {chain_name}")
    
    def show_summary(self):
        """Show database summary"""
        with get_db() as db:
            logger.info("\n" + "="*50)
            logger.info("📊 DATABASE SUMMARY")
            logger.info("="*50 + "\n")
            
            # Chains and branches
            chains = db.query(Chain).all()
            for chain in chains:
                branch_count = db.query(Branch).filter(Branch.chain_id == chain.chain_id).count()
                product_count = db.query(ChainProduct).filter(ChainProduct.chain_id == chain.chain_id).count()
                
                logger.info(f"{chain.display_name} ({chain.name}):")
                logger.info(f"  - Branches: {branch_count}")
                logger.info(f"  - Products: {product_count}")
            
            # Top cities
            cities = db.query(
                Branch.city,
                func.count(Branch.branch_id).label('count')
            ).group_by(Branch.city)\
             .order_by(func.count(Branch.branch_id).desc())\
             .limit(10)\
             .all()
            
            logger.info(f"\n🏙️  Top 10 Cities:")
            for city, count in cities:
                logger.info(f"  {city}: {count} stores")
            
            # Total statistics
            total_branches = db.query(Branch).count()
            total_products = db.query(ChainProduct).count()
            total_prices = db.query(BranchPrice).count()
            
            logger.info(f"\n📈 Totals:")
            logger.info(f"  - Total branches: {total_branches}")
            logger.info(f"  - Total products: {total_products}")
            logger.info(f"  - Total prices: {total_prices}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Import chain data')
    parser.add_argument('--chain', type=str, help='Specific chain to import (default: all)')
    parser.add_argument('--stores-only', action='store_true', help='Import only stores, not prices')
    parser.add_argument('--list-chains', action='store_true', help='List available chains')
    
    args = parser.parse_args()
    
    if args.list_chains:
        print("\nAvailable chains:")
        for chain_name in PARSER_REGISTRY.keys():
            print(f"  - {chain_name}")
        return
    
    importer = ChainDataImporter()
    
    # Determine which chains to import
    chains_to_import = [args.chain] if args.chain else list(PARSER_REGISTRY.keys())
    
    # Import data
    for chain_name in chains_to_import:
        try:
            importer.import_chain_data(chain_name, include_prices=not args.stores_only)
        except Exception as e:
            logger.error(f"Failed to import {chain_name}: {e}")
    
    # Show summary
    importer.show_summary()


if __name__ == "__main__":
    main()