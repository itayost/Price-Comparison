# price_comparison_server/parsers/base_parser.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import requests
import gzip
from io import BytesIO
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class BaseChainParser(ABC):
    """Abstract base class for chain parsers"""
    
    def __init__(self, chain_name: str, chain_id: str):
        self.chain_name = chain_name
        self.chain_id = chain_id
        self.base_url = None
        
    @abstractmethod
    def get_store_file_urls(self) -> List[str]:
        """Get list of store file URLs to download"""
        pass
    
    @abstractmethod
    def get_price_file_urls(self) -> List[str]:
        """Get list of price file URLs to download"""
        pass
    
    @abstractmethod
    def parse_store_data(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parse store data from XML content"""
        pass
    
    @abstractmethod
    def parse_price_data(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parse price data from XML content"""
        pass
    
    def download_gz_file(self, url: str) -> Optional[bytes]:
        """Download and extract GZ file"""
        try:
            logger.info(f"Downloading: {url}")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                with gzip.GzipFile(fileobj=BytesIO(response.content)) as f:
                    return f.read()
            else:
                logger.error(f"Failed to download {url}: Status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading {url}: {str(e)}")
            return None
    
    def scrape_file_list(self, list_url: str, link_selector: Dict[str, Any], 
                        file_type_identifier: str) -> List[str]:
        """
        Generic method to scrape file lists from index pages
        
        Args:
            list_url: URL of the page listing files
            link_selector: Dict with 'tag' and search parameters for BeautifulSoup
            file_type_identifier: String to identify the type of file
        """
        try:
            response = requests.get(list_url, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to fetch {list_url}: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract tag and search parameters
            tag = link_selector.get('tag', 'a')
            
            # Handle different ways of specifying the search
            if 'text' in link_selector:
                # Use text parameter directly
                links = soup.find_all(tag, text=link_selector['text'])
            elif 'string' in link_selector:
                # Use string parameter (newer BeautifulSoup)
                links = soup.find_all(tag, string=link_selector['string'])
            elif 'attrs' in link_selector:
                # Use attributes
                links = soup.find_all(tag, attrs=link_selector['attrs'])
            else:
                # Just find all tags
                links = soup.find_all(tag)
            
            file_urls = []
            for link in links:
                href = link.get('href')
                if href and file_type_identifier in href:
                    # Handle relative URLs
                    if not href.startswith('http'):
                        href = self.base_url + href if self.base_url else href
                    file_urls.append(href)
                    
            logger.info(f"Found {len(file_urls)} {file_type_identifier} files")
            return file_urls
            
        except Exception as e:
            logger.error(f"Error scraping {list_url}: {e}")
            return []
    
    def process_stores(self) -> List[Dict[str, Any]]:
        """Process all store files and return parsed data"""
        all_stores = []
        
        urls = self.get_store_file_urls()
        for i, url in enumerate(urls):
            logger.info(f"Processing store file {i+1}/{len(urls)} for {self.chain_name}")
            content = self.download_gz_file(url)
            
            if content:
                stores = self.parse_store_data(content)
                all_stores.extend(stores)
                logger.info(f"Parsed {len(stores)} stores from file")
                
        return all_stores
    
    def process_prices(self, branch_id_mapping: Dict[str, int]) -> List[Dict[str, Any]]:
        """Process all price files and return parsed data"""
        all_prices = []
        
        urls = self.get_price_file_urls()
        for i, url in enumerate(urls):
            logger.info(f"Processing price file {i+1}/{len(urls)} for {self.chain_name}")
            content = self.download_gz_file(url)
            
            if content:
                prices = self.parse_price_data(content)
                # Map store IDs to branch IDs
                for price in prices:
                    if price['store_id'] in branch_id_mapping:
                        price['branch_id'] = branch_id_mapping[price['store_id']]
                        all_prices.append(price)
                        
                logger.info(f"Parsed {len(prices)} prices from file")
                
        return all_prices