#!/usr/bin/env python3
# price_comparison_server/scripts/test_store_import.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_shufersal_direct():
    """Test Shufersal scraping directly"""
    logger.info("Testing Shufersal store file discovery...")
    
    url = 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=5'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, timeout=30, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links
            all_links = soup.find_all('a')
            store_links = []
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Check if this is a store file
                if 'StoresFull' in href:
                    store_links.append({
                        'text': text,
                        'href': href
                    })
            
            logger.info(f"Found {len(store_links)} store file links")
            
            # Show first few
            for i, link in enumerate(store_links[:3]):
                logger.info(f"  {i+1}. Text: '{link['text']}' -> {link['href'][:80]}...")
                
            return len(store_links) > 0
        else:
            logger.error(f"Failed to fetch page: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


def test_victory_direct():
    """Test Victory scraping directly"""
    logger.info("\nTesting Victory store file discovery...")
    
    url = 'https://laibcatalog.co.il/NBCompetitionRegulations.aspx?code=7290696200003&fileType=storesfull'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, timeout=60, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links
            all_links = soup.find_all('a')
            store_links = []
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Check if this is a download link
                if 'להורדה' in text and ('stores' in href.lower() or '.gz' in href):
                    store_links.append({
                        'text': text,
                        'href': href
                    })
            
            logger.info(f"Found {len(store_links)} store file links")
            
            # Show first few
            for i, link in enumerate(store_links[:3]):
                logger.info(f"  {i+1}. Text: '{link['text']}' -> {link['href'][:80]}...")
                
            return len(store_links) > 0
        else:
            logger.error(f"Failed to fetch page: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


def main():
    """Run tests"""
    logger.info("=== Testing Store File Discovery ===\n")
    
    shufersal_ok = test_shufersal_direct()
    victory_ok = test_victory_direct()
    
    logger.info("\n=== Summary ===")
    logger.info(f"Shufersal: {'✅ Working' if shufersal_ok else '❌ Not working'}")
    logger.info(f"Victory: {'✅ Working' if victory_ok else '❌ Not working'}")
    
    if not (shufersal_ok and victory_ok):
        logger.info("\n🔧 Suggested fixes:")
        if not shufersal_ok:
            logger.info("- Check if Shufersal changed their website structure")
            logger.info("- Try using pagination: add &page=1 to the URL")
        if not victory_ok:
            logger.info("- Victory site might be blocking automated requests")
            logger.info("- Try adding more headers or using a session")


if __name__ == "__main__":
    main()