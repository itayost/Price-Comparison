#!/usr/bin/env python3
# price_comparison_server/scripts/diagnose_scraping.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import requests
from bs4 import BeautifulSoup
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_shufersal_pages():
    """Test different Shufersal pages and approaches"""
    logger.info("=== Testing Shufersal ===\n")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'he-IL,he;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    # Test different URLs
    test_urls = [
        ('Store files page', 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=5'),
        ('Store files with page', 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=5&storeId=0&page=1'),
        ('Price files page', 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=2'),
        ('Main page', 'https://prices.shufersal.co.il/'),
    ]
    
    for name, url in test_urls:
        logger.info(f"Testing {name}: {url}")
        try:
            response = requests.get(url, timeout=30, headers=headers)
            logger.info(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for any links
                all_links = soup.find_all('a')
                logger.info(f"  Total links found: {len(all_links)}")
                
                # Look for download links
                download_links = []
                store_links = []
                
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Log first few links for debugging
                    if len(download_links) < 3 and href:
                        logger.info(f"    Sample link: '{text[:30]}...' -> {href[:60]}...")
                    
                    if 'להורדה' in text or 'download' in text.lower():
                        download_links.append(link)
                    
                    if 'StoresFull' in href or 'stores' in href.lower():
                        store_links.append(link)
                
                logger.info(f"  Download links: {len(download_links)}")
                logger.info(f"  Store file links: {len(store_links)}")
                
                # Check page content
                page_text = soup.get_text()
                if 'StoresFull' in page_text:
                    logger.info("  ✓ Found 'StoresFull' in page text")
                if 'להורדה' in page_text:
                    logger.info("  ✓ Found 'להורדה' (download) in page text")
                
                # Look for specific patterns
                if response.url != url:
                    logger.info(f"  Redirected to: {response.url}")
                    
            time.sleep(1)  # Be polite
            
        except Exception as e:
            logger.error(f"  Error: {e}")
        
        logger.info("")


def test_victory_approaches():
    """Test different approaches for Victory"""
    logger.info("=== Testing Victory ===\n")
    
    # Try with session and more complete headers
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    })
    
    # Test URLs
    test_urls = [
        ('Store files', 'https://laibcatalog.co.il/NBCompetitionRegulations.aspx?code=7290696200003&fileType=storesfull'),
        ('Price files', 'https://laibcatalog.co.il/NBCompetitionRegulations.aspx?code=7290696200003&fileType=pricefull'),
        ('Main regulations page', 'https://laibcatalog.co.il/NBCompetitionRegulations.aspx'),
    ]
    
    for name, url in test_urls:
        logger.info(f"Testing {name}: {url}")
        try:
            # First, try to get the main page to establish session
            if 'storesfull' in url or 'pricefull' in url:
                main_url = 'https://laibcatalog.co.il/'
                logger.info("  First visiting main page...")
                main_resp = session.get(main_url, timeout=30)
                logger.info(f"  Main page status: {main_resp.status_code}")
                time.sleep(2)
            
            # Now try the actual URL
            response = session.get(url, timeout=60)
            logger.info(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for links
                all_links = soup.find_all('a')
                logger.info(f"  Total links: {len(all_links)}")
                
                # Sample some links
                for i, link in enumerate(all_links[:5]):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if text or href:
                        logger.info(f"    Link {i+1}: '{text[:30]}...' -> {href[:50]}...")
                
                # Check for download patterns
                download_count = 0
                for link in all_links:
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    if 'להורדה' in text or 'download' in text.lower() or '.gz' in href:
                        download_count += 1
                        logger.info(f"    Download link found: '{text}' -> {href[:60]}...")
                
                logger.info(f"  Total download links: {download_count}")
                
            time.sleep(2)
            
        except requests.exceptions.Timeout:
            logger.error("  Timeout - site might be slow or blocking")
        except Exception as e:
            logger.error(f"  Error: {e}")
        
        logger.info("")


def check_alternative_sources():
    """Check if we can find alternative data sources"""
    logger.info("=== Checking Alternative Approaches ===\n")
    
    # Check if the sites have robots.txt or sitemap
    for chain, base_url in [('Shufersal', 'https://prices.shufersal.co.il'), 
                            ('Victory', 'https://laibcatalog.co.il')]:
        logger.info(f"Checking {chain}...")
        
        # Try robots.txt
        try:
            robots_url = f"{base_url}/robots.txt"
            resp = requests.get(robots_url, timeout=10)
            if resp.status_code == 200:
                logger.info(f"  robots.txt found!")
                logger.info(f"  Content preview: {resp.text[:200]}...")
        except:
            logger.info(f"  No robots.txt accessible")
        
        # Try sitemap
        try:
            sitemap_url = f"{base_url}/sitemap.xml"
            resp = requests.get(sitemap_url, timeout=10)
            if resp.status_code == 200:
                logger.info(f"  sitemap.xml found!")
        except:
            logger.info(f"  No sitemap.xml accessible")
        
        logger.info("")


def main():
    """Run all diagnostics"""
    logger.info("=== Diagnosing Scraping Issues ===\n")
    logger.info("This may take a few minutes...\n")
    
    test_shufersal_pages()
    test_victory_approaches()
    check_alternative_sources()
    
    logger.info("\n=== Recommendations ===")
    logger.info("1. Check if the sites have changed their structure")
    logger.info("2. Consider using Selenium for JavaScript-rendered content")
    logger.info("3. Check if there's an official API or data feed")
    logger.info("4. Verify if manual access works from your browser")
    logger.info("5. Consider reaching out to the chains for official data access")


if __name__ == "__main__":
    main()