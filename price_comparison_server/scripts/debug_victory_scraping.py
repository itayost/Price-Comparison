#!/usr/bin/env python3
# price_comparison_server/scripts/debug_victory_scraping.py

import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_victory():
    """Debug Victory website scraping"""
    url = 'https://laibcatalog.co.il/NBCompetitionRegulations.aspx?code=7290696200003&fileType=storesfull'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'he-IL,he;q=0.9,en;q=0.8',
    }
    
    try:
        logger.info(f"Fetching: {url}")
        response = requests.get(url, timeout=30, headers=headers)
        logger.info(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links
            all_links = soup.find_all('a')
            logger.info(f"\nTotal links found: {len(all_links)}")
            
            # Look for download links with different methods
            logger.info("\nSearching for download links...")
            
            # Method 1: text='לחץ כאן להורדה'
            links1 = soup.find_all('a', text='לחץ כאן להורדה')
            logger.info(f"Method 1 (text=): {len(links1)} links")
            
            # Method 2: string='לחץ כאן להורדה'
            links2 = soup.find_all('a', string='לחץ כאן להורדה')
            logger.info(f"Method 2 (string=): {len(links2)} links")
            
            # Method 3: Check all links for Hebrew text
            download_links = []
            for link in all_links:
                link_text = link.get_text(strip=True)
                href = link.get('href', '')
                
                # Log first 10 links for debugging
                if len(all_links) <= 10 or all_links.index(link) < 10:
                    logger.info(f"\nLink {all_links.index(link)+1}:")
                    logger.info(f"  Text: '{link_text}'")
                    logger.info(f"  Href: {href[:80]}...")
                
                if 'להורדה' in link_text:
                    download_links.append(link)
                    logger.info(f"\nFound download link!")
                    logger.info(f"  Text: '{link_text}'")
                    logger.info(f"  Href: {href}")
            
            logger.info(f"\nTotal download links found: {len(download_links)}")
            
            # Check for stores files
            stores_files = []
            for link in download_links:
                href = link.get('href', '')
                if 'stores' in href.lower() or 'StoresFull' in href:
                    stores_files.append(href)
                    logger.info(f"\nStores file found: {href}")
            
            logger.info(f"\nTotal stores files: {len(stores_files)}")
            
            # Check page encoding
            logger.info(f"\nPage encoding: {response.encoding}")
            
        else:
            logger.error(f"Failed to fetch page: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_victory()