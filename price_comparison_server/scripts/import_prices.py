#!/usr/bin/env python3
# price_comparison_server/scripts/import_prices.py

import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db
from database.new_models import Chain, Branch, ChainProduct, BranchPrice
from parsers import get_parser
from sqlalchemy import func

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PriceImporter:
    """Import price data using the new schema"""
    
    def __init__(self):
        self.stats = {
            'products_created': 0,
            'products_updated': 0,
            'prices_created': 0,
            'prices_updated': 0,
            'errors': 0
        }
    
    def import_chain_prices(self, chain_name: str, limit_files: int = None):
        """Import prices for a specific chain"""
        logger.info(f"\n{'='*50}")
        logger.info(f"Importing prices for {chain_name.upper()}")
        logger.info(f"{'='*50}")
        
        # Get parser
        parser = get_parser(chain_name)
        
        # Get branch mappings
        branch_mappings = self.get_branch_mappings(chain_name)
        if not branch_mappings:
            logger.error(f"No branches found for {chain_name}")
            return
        
        logger.info(f"Found {len(branch_mappings)} branches for {chain_name}")
        
        # Get price file URLs
        logger.info("Fetching price file URLs...")
        price_urls = parser.get_price_file_urls()
        
        if not price_urls:
            logger.warning(f"No price files found for {chain_name}")
            return
        
        logger.info(f"Found {len(price_urls)} price files")
        
        # Limit files if requested (for testing)
        if limit_files:
            price_urls = price_urls[:limit_files]
            logger.info(f"Limited to {len(price_urls)} files for testing")
        
        # Process each price file
        for i, url in enumerate(price_urls, 1):
            logger.info(f"\nProcessing file {i}/{len(price_urls)}")
            self.process_price_file(chain_name, parser, url, branch_mappings)
            
            # Log progress every 5 files
            if i % 5 == 0:
                self.log_progress()
    
    def get_branch_mappings(self, chain_name: str) -> Dict[str, int]:
        """Get mapping of store_id to branch_id for a chain"""
        mappings = {}
        
        with get_db() as db:
            chain = db.query(Chain).filter(Chain.name == chain_name).first()
            if not chain:
                return mappings
            
            branches = db.query(Branch).filter(Branch.chain_id == chain.chain_id).all()
            for branch in branches:
                mappings[branch.store_id] = branch.branch_id
                
        return mappings
    
    def process_price_file(self, chain_name: str, parser, url: str, branch_mappings: Dict[str, int]):
        """Process a single price file"""
        try:
            # Download and parse file
            logger.info(f"Downloading: {url}")
            content = parser.download_gz_file(url)
            
            if not content:
                logger.error(f"Failed to download {url}")
                self.stats['errors'] += 1
                return
            
            # Parse prices
            prices = parser.parse_price_data(content)
            logger.info(f"Parsed {len(prices)} prices")
            
            if not prices:
                return
            
            # Import prices in batches
            self.import_price_batch(chain_name, prices, branch_mappings)
            
        except Exception as e:
            logger.error(f"Error processing price file: {e}")
            self.stats['errors'] += 1
    
    def import_price_batch(self, chain_name: str, prices: List[Dict], branch_mappings: Dict[str, int]):
        """Import a batch of prices"""
        with get_db() as db:
            chain = db.query(Chain).filter(Chain.name == chain_name).first()
            if not chain:
                return
            
            # Process in smaller batches
            batch_size = 1000
            for i in range(0, len(prices), batch_size):
                batch = prices[i:i + batch_size]
                
                for price_data in batch:
                    try:
                        # Skip if branch not found
                        store_id = price_data.get('store_id')
                        if store_id not in branch_mappings:
                            continue
                        
                        branch_id = branch_mappings[store_id]
                        
                        # Get or create chain product
                        barcode = price_data.get('barcode')
                        if not barcode:
                            continue
                        
                        chain_product = db.query(ChainProduct).filter(
                            ChainProduct.chain_id == chain.chain_id,
                            ChainProduct.barcode == barcode
                        ).first()
                        
                        if not chain_product:
                            # Create new chain product
                            chain_product = ChainProduct(
                                chain_id=chain.chain_id,
                                barcode=barcode,
                                name=price_data.get('name', f'Product {barcode}')
                            )
                            db.add(chain_product)
                            db.flush()
                            self.stats['products_created'] += 1
                        else:
                            # Update name if better
                            if price_data.get('name') and len(price_data['name']) > len(chain_product.name or ''):
                                chain_product.name = price_data['name']
                                self.stats['products_updated'] += 1
                        
                        # Get or create price
                        branch_price = db.query(BranchPrice).filter(
                            BranchPrice.chain_product_id == chain_product.chain_product_id,
                            BranchPrice.branch_id == branch_id
                        ).first()
                        
                        if branch_price:
                            # Update existing price
                            branch_price.price = price_data['price']
                            branch_price.last_updated = datetime.utcnow()
                            self.stats['prices_updated'] += 1
                        else:
                            # Create new price
                            branch_price = BranchPrice(
                                chain_product_id=chain_product.chain_product_id,
                                branch_id=branch_id,
                                price=price_data['price'],
                                last_updated=datetime.utcnow()
                            )
                            db.add(branch_price)
                            self.stats['prices_created'] += 1
                            
                    except Exception as e:
                        logger.debug(f"Error processing price: {e}")
                        self.stats['errors'] += 1
                        continue
                
                # Commit batch
                db.commit()
                
            logger.info(f"Imported batch: {len(batch)} items")
    
    def log_progress(self):
        """Log current progress"""
        logger.info(f"\nProgress Update:")
        logger.info(f"  Products created: {self.stats['products_created']}")
        logger.info(f"  Products updated: {self.stats['products_updated']}")
        logger.info(f"  Prices created: {self.stats['prices_created']}")
        logger.info(f"  Prices updated: {self.stats['prices_updated']}")
        logger.info(f"  Errors: {self.stats['errors']}")
    
    def show_summary(self):
        """Show final summary"""
        logger.info(f"\n{'='*50}")
        logger.info("IMPORT SUMMARY")
        logger.info(f"{'='*50}")
        
        self.log_progress()
        
        # Show database totals
        with get_db() as db:
            total_products = db.query(func.count(ChainProduct.chain_product_id)).scalar()
            total_prices = db.query(func.count(BranchPrice.price_id)).scalar()
            
            logger.info(f"\nDatabase Totals:")
            logger.info(f"  Total products: {total_products}")
            logger.info(f"  Total prices: {total_prices}")
            
            # Show per-chain breakdown
            logger.info(f"\nPer-chain breakdown:")
            chains = db.query(Chain).all()
            for chain in chains:
                product_count = db.query(func.count(ChainProduct.chain_product_id))\
                    .filter(ChainProduct.chain_id == chain.chain_id).scalar()
                
                price_count = db.query(func.count(BranchPrice.price_id))\
                    .join(ChainProduct)\
                    .filter(ChainProduct.chain_id == chain.chain_id).scalar()
                
                logger.info(f"  {chain.display_name}:")
                logger.info(f"    - Products: {product_count}")
                logger.info(f"    - Prices: {price_count}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import price data')
    parser.add_argument('--chain', choices=['shufersal', 'victory', 'all'], 
                       default='all', help='Chain to import')
    parser.add_argument('--limit', type=int, help='Limit number of files to process (for testing)')
    args = parser.parse_args()
    
    importer = PriceImporter()
    
    try:
        if args.chain == 'all':
            importer.import_chain_prices('shufersal', args.limit)
            importer.import_chain_prices('victory', args.limit)
        else:
            importer.import_chain_prices(args.chain, args.limit)
            
        importer.show_summary()
        
    except KeyboardInterrupt:
        logger.info("\nImport interrupted by user")
        importer.show_summary()
    except Exception as e:
        logger.error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()