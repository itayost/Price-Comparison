#!/usr/bin/env python3
# price_comparison_server/scripts/debug_price_parsing.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers import get_parser
import logging
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_shufersal_price_parsing():
    """Test Shufersal price file parsing"""
    logger.info("=== Testing Shufersal Price Parsing ===")
    
    parser = get_parser('shufersal')
    
    # Get price URLs
    urls = parser.get_price_file_urls()
    logger.info(f"Found {len(urls)} price file URLs")
    
    if urls:
        # Download first file
        logger.info(f"\nDownloading first price file...")
        content = parser.download_gz_file(urls[0])
        
        if content:
            # Check XML structure
            logger.info("Checking XML structure...")
            root = ET.fromstring(content)
            logger.info(f"Root tag: {root.tag}")
            
            # Check for store ID
            store_id_fields = ['StoreId', 'StoreID', 'STOREID']
            for field in store_id_fields:
                elem = root.find(f'.//{field}')
                if elem is not None:
                    logger.info(f"Found store ID in field '{field}': {elem.text}")
                    break
            
            # Check product structure
            products = root.findall('.//Product')
            if not products:
                products = root.findall('.//Item')
            if not products:
                products = root.findall('.//PRODUCT')
            
            logger.info(f"Found {len(products)} product elements")
            
            if products:
                # Check first product
                product = products[0]
                logger.info("\nFirst product structure:")
                for child in product:
                    logger.info(f"  {child.tag}: {child.text}")
                
                # Parse a few products
                logger.info("\nParsing first 3 products:")
                parsed = parser.parse_price_data(content)
                for i, p in enumerate(parsed[:3]):
                    logger.info(f"\nProduct {i+1}:")
                    logger.info(f"  Store ID: {p.get('store_id')}")
                    logger.info(f"  Barcode: {p.get('barcode')}")
                    logger.info(f"  Name: {p.get('name')}")
                    logger.info(f"  Price: {p.get('price')}")


def test_victory_price_urls():
    """Test Victory price URL fetching"""
    logger.info("\n\n=== Testing Victory Price URLs ===")
    
    import requests
    from bs4 import BeautifulSoup
    
    url = 'https://laibcatalog.co.il/NBCompetitionRegulations.aspx?code=7290696200003&fileType=pricefull'
    
    logger.info(f"Fetching: {url}")
    response = requests.get(url, timeout=30)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find download links
        links = soup.find_all('a', string='לחץ כאן להורדה')
        logger.info(f"Found {len(links)} download links")
        
        for i, link in enumerate(links):
            href = link.get('href', '')
            logger.info(f"\nLink {i+1}: {href}")
            
            # Check if it's a price file
            if 'price' in href.lower():
                logger.info("  ✓ Contains 'price'")
                
                # Build full URL
                if not href.startswith('http'):
                    href = href.replace('\\', '/')
                    full_url = 'https://laibcatalog.co.il/' + href.lstrip('/')
                    logger.info(f"  Full URL: {full_url}")


def check_branch_mappings():
    """Check if branch mappings are working"""
    logger.info("\n\n=== Checking Branch Mappings ===")
    
    from database.connection import get_db
    from database.new_models import Chain, Branch
    
    with get_db() as db:
        # Check Shufersal branches
        chain = db.query(Chain).filter(Chain.name == 'shufersal').first()
        if chain:
            branches = db.query(Branch).filter(Branch.chain_id == chain.chain_id).limit(5).all()
            logger.info(f"\nSample Shufersal branches:")
            for branch in branches:
                logger.info(f"  Store ID: {branch.store_id} -> Branch ID: {branch.branch_id}")


if __name__ == "__main__":
    test_shufersal_price_parsing()
    test_victory_price_urls()
    check_branch_mappings()