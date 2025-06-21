#!/usr/bin/env python3
# price_comparison_server/scripts/debug_victory_detailed.py

import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_victory():
    """Debug Victory website - show full download links"""
    url = 'https://laibcatalog.co.il/NBCompetitionRegulations.aspx?code=7290696200003&fileType=storesfull'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        response = requests.get(url, timeout=30, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find download links using string parameter
            download_links = soup.find_all('a', string='לחץ כאן להורדה')
            
            logger.info(f"Found {len(download_links)} download links")
            
            for i, link in enumerate(download_links):
                href = link.get('href', '')
                logger.info(f"\nDownload link {i+1}:")
                logger.info(f"Full href: {href}")
                
                # Check what's in the URL
                if 'stores' in href.lower():
                    logger.info("✓ Contains 'stores' (case-insensitive)")
                if 'StoresFull' in href:
                    logger.info("✓ Contains 'StoresFull'")
                if '.gz' in href:
                    logger.info("✓ Contains '.gz'")
                    
                # Build full URL if relative
                if not href.startswith('http'):
                    full_url = 'https://laibcatalog.co.il/' + href.lstrip('/')
                    logger.info(f"Full URL would be: {full_url}")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    debug_victory()