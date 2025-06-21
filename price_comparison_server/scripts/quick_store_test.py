#!/usr/bin/env python3
# price_comparison_server/scripts/quick_store_test.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import requests
from bs4 import BeautifulSoup
import gzip
from io import BytesIO
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_shufersal_stores():
    """Test downloading and parsing Shufersal store file"""
    logger.info("=== Testing Shufersal Stores ===")
    
    # Step 1: Get the download URL
    url = 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=5'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, timeout=30, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find download link
        download_link = None
        for link in soup.find_all('a', text='לחץ להורדה'):
            href = link.get('href')
            if href and 'Stores' in href:
                download_link = href
                break
        
        if not download_link:
            logger.error("No store download link found")
            return False
            
        logger.info(f"Found download link: {download_link[:80]}...")
        
        # Step 2: Download the file
        logger.info("Downloading store file...")
        file_response = requests.get(download_link, timeout=60, headers=headers)
        
        if file_response.status_code != 200:
            logger.error(f"Failed to download: {file_response.status_code}")
            return False
        
        # Step 3: Extract and parse
        logger.info("Extracting GZ file...")
        with gzip.GzipFile(fileobj=BytesIO(file_response.content)) as f:
            xml_content = f.read()
        
        logger.info("Parsing XML...")
        root = ET.fromstring(xml_content)
        
        # Find stores
        stores = root.findall('.//Store')
        logger.info(f"Found {len(stores)} stores")
        
        # Show sample store
        if stores:
            store = stores[0]
            logger.info("\nSample store:")
            for child in store:
                if child.text:
                    logger.info(f"  {child.tag}: {child.text}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


def test_victory_stores():
    """Test downloading and parsing Victory store file"""
    logger.info("\n=== Testing Victory Stores ===")
    
    # Step 1: Get the download URL
    url = 'https://laibcatalog.co.il/NBCompetitionRegulations.aspx?code=7290696200003&fileType=storesfull'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, timeout=30, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find download link
        download_link = None
        for link in soup.find_all('a'):
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if 'להורדה' in text and ('stores' in href.lower() or '.gz' in href):
                download_link = href
                if not download_link.startswith('http'):
                    download_link = 'https://laibcatalog.co.il/' + download_link
                break
        
        if not download_link:
            logger.error("No store download link found")
            return False
            
        logger.info(f"Found download link: {download_link[:80]}...")
        
        # Step 2: Download the file
        logger.info("Downloading store file...")
        file_response = requests.get(download_link, timeout=60, headers=headers)
        
        if file_response.status_code != 200:
            logger.error(f"Failed to download: {file_response.status_code}")
            return False
        
        # Step 3: Extract and parse
        logger.info("Extracting GZ file...")
        with gzip.GzipFile(fileobj=BytesIO(file_response.content)) as f:
            xml_content = f.read()
        
        logger.info("Parsing XML...")
        root = ET.fromstring(xml_content)
        
        # Find stores
        stores = root.findall('.//Store')
        logger.info(f"Found {len(stores)} stores")
        
        # Show sample store
        if stores:
            store = stores[0]
            logger.info("\nSample store:")
            for child in store:
                if child.text:
                    logger.info(f"  {child.tag}: {child.text}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


def main():
    """Run tests"""
    shufersal_ok = test_shufersal_stores()
    victory_ok = test_victory_stores()
    
    logger.info("\n=== Summary ===")
    logger.info(f"Shufersal: {'✅ SUCCESS' if shufersal_ok else '❌ FAILED'}")
    logger.info(f"Victory: {'✅ SUCCESS' if victory_ok else '❌ FAILED'}")
    
    if shufersal_ok and victory_ok:
        logger.info("\n✅ Both chains are working! You can now:")
        logger.info("1. Replace your parser files with the working versions")
        logger.info("2. Run the import script: python3 scripts/import_chain_data.py --stores-only")


if __name__ == "__main__":
    main()