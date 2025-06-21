#!/usr/bin/env python3
# price_comparison_server/scripts/debug_scraping.py

import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_shufersal_scraping():
    """Test Shufersal store file scraping"""
    logger.info("Testing Shufersal store scraping...")
    
    url = 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=5'
    
    try:
        response = requests.get(url, timeout=30)
        logger.info(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try different methods to find links
            logger.info("\nMethod 1: find_all with text")
            links1 = soup.find_all('a', text='לחץ להורדה')
            logger.info(f"Found {len(links1)} links with text='לחץ להורדה'")
            
            logger.info("\nMethod 2: find_all with string")
            links2 = soup.find_all('a', string='לחץ להורדה')
            logger.info(f"Found {len(links2)} links with string='לחץ להורדה'")
            
            logger.info("\nMethod 3: find all <a> tags and filter")
            all_links = soup.find_all('a')
            logger.info(f"Total <a> tags: {len(all_links)}")
            
            # Check what text is in the links
            download_links = []
            for link in all_links[:20]:  # Check first 20 links
                link_text = link.get_text(strip=True)
                href = link.get('href', '')
                if link_text:
                    logger.info(f"Link text: '{link_text}' -> href: {href[:50]}...")
                if 'להורדה' in link_text:
                    download_links.append(link)
            
            logger.info(f"\nFound {len(download_links)} download links")
            
            # Look for StoresFull files
            store_files = []
            for link in download_links:
                href = link.get('href', '')
                if 'StoresFull' in href:
                    store_files.append(href)
            
            logger.info(f"\nFound {len(store_files)} StoresFull files")
            for i, file_url in enumerate(store_files[:5]):
                logger.info(f"{i+1}. {file_url}")
                
    except Exception as e:
        logger.error(f"Error: {e}")


def test_victory_scraping():
    """Test Victory store file scraping"""
    logger.info("\n\nTesting Victory store scraping...")
    
    url = 'https://laibcatalog.co.il/NBCompetitionRegulations.aspx?code=7290696200003&fileType=storesfull'
    
    try:
        # Use headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, timeout=30, headers=headers)
        logger.info(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try different methods
            logger.info("\nMethod 1: find_all with string")
            links1 = soup.find_all('a', string='לחץ כאן להורדה')
            logger.info(f"Found {len(links1)} links with string='לחץ כאן להורדה'")
            
            logger.info("\nMethod 2: find_all with text")
            links2 = soup.find_all('a', text='לחץ כאן להורדה')
            logger.info(f"Found {len(links2)} links with text='לחץ כאן להורדה'")
            
            # Check all links
            all_links = soup.find_all('a')
            logger.info(f"\nTotal <a> tags: {len(all_links)}")
            
            download_links = []
            for link in all_links:
                link_text = link.get_text(strip=True)
                href = link.get('href', '')
                if 'להורדה' in link_text:
                    logger.info(f"Download link: '{link_text}' -> {href[:50]}...")
                    download_links.append(link)
            
            # Look for store files
            store_files = []
            for link in download_links:
                href = link.get('href', '')
                if 'stores' in href.lower():
                    store_files.append(href)
            
            logger.info(f"\nFound {len(store_files)} store files")
            for i, file_url in enumerate(store_files[:5]):
                logger.info(f"{i+1}. {file_url}")
                
    except Exception as e:
        logger.error(f"Error: {e}")


def main():
    """Run all tests"""
    test_shufersal_scraping()
    test_victory_scraping()


if __name__ == "__main__":
    main()