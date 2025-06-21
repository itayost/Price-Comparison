# price_comparison_server/parsers/victory_parser.py

import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from .base_parser import BaseChainParser
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class VictoryParser(BaseChainParser):
    """Parser for Victory chain data"""
    
    def __init__(self):
        super().__init__('victory', '7290696200003')
        self.base_url = 'https://laibcatalog.co.il'
        self.stores_list_url = 'https://laibcatalog.co.il/NBCompetitionRegulations.aspx?code=7290696200003&fileType=storesfull'
        self.prices_list_url = 'https://laibcatalog.co.il/NBCompetitionRegulations.aspx?code=7290696200003&fileType=pricefull'
        
    def get_store_file_urls(self) -> List[str]:
        """Get Victory store file URLs - Fixed for case sensitivity and path issues"""
        try:
            response = requests.get(self.stores_list_url, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to fetch {self.stores_list_url}: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find links with the download text
            links = soup.find_all('a', string='לחץ כאן להורדה')
            if not links:
                # Try with text parameter for older BeautifulSoup
                links = soup.find_all('a', text='לחץ כאן להורדה')
            
            file_urls = []
            for link in links:
                href = link.get('href')
                if href:
                    # Case-insensitive check for stores files
                    if 'stores' in href.lower() or 'storesfull' in href.lower():
                        # Fix mixed slashes
                        href = href.replace('\\', '/')
                        
                        # Handle relative URLs
                        if not href.startswith('http'):
                            href = self.base_url + '/' + href.lstrip('/')
                            
                        file_urls.append(href)
                        logger.info(f"Found Victory store file: {href}")
                        
            logger.info(f"Found {len(file_urls)} stores files")
            return file_urls
            
        except Exception as e:
            logger.error(f"Error scraping Victory store files: {e}")
            return []
    
    def get_price_file_urls(self) -> List[str]:
        """Get Victory price file URLs - Fixed for case sensitivity and path issues"""
        try:
            response = requests.get(self.prices_list_url, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to fetch {self.prices_list_url}: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find links with the download text
            links = soup.find_all('a', string='לחץ כאן להורדה')
            if not links:
                links = soup.find_all('a', text='לחץ כאן להורדה')
            
            file_urls = []
            for link in links:
                href = link.get('href')
                if href:
                    # Case-insensitive check for price files
                    if 'price' in href.lower():
                        # Fix mixed slashes
                        href = href.replace('\\', '/')
                        
                        # Handle relative URLs
                        if not href.startswith('http'):
                            href = self.base_url + '/' + href.lstrip('/')
                            
                        file_urls.append(href)
                        logger.info(f"Found Victory price file: {href}")
                        
            logger.info(f"Found {len(file_urls)} price files")
            return file_urls
            
        except Exception as e:
            logger.error(f"Error scraping Victory price files: {e}")
            return []
    
    def parse_store_data(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parse Victory store XML format - Fixed for actual structure"""
        stores = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Victory structure: /Store/Branches/Branch
            branches = root.find('.//Branches')
            if branches is None:
                logger.error("No Branches element found in Victory XML")
                return stores
            
            store_elements = branches.findall('Branch')
            logger.info(f"Found {len(store_elements)} store elements in Victory XML")
            
            for store in store_elements:
                try:
                    # Extract store data - Victory uses mixed case
                    store_id_elem = store.find('StoreID')
                    if store_id_elem is None or not store_id_elem.text:
                        continue
                    
                    chain_id_elem = store.find('ChainID')
                    chain_id = chain_id_elem.text if chain_id_elem is not None else self.chain_id
                    
                    store_data = {
                        'chain_id': chain_id,
                        'store_id': store_id_elem.text.strip(),
                        'sub_chain_id': store.find('SubChainID').text if store.find('SubChainID') is not None else '001',
                        'store_name': store.find('StoreName').text if store.find('StoreName') is not None else f"Store {store_id_elem.text}",
                        'address': store.find('Address').text if store.find('Address') is not None else "Unknown",
                        'city': store.find('City').text.strip() if store.find('City') is not None and store.find('City').text else "Unknown",
                        'store_type': store.find('StoreType').text if store.find('StoreType') is not None else None,
                    }
                    
                    # Create full store ID
                    store_data['full_store_id'] = f"{chain_id}-{store_data['sub_chain_id']}-{store_data['store_id']}"
                    
                    stores.append(store_data)
                    logger.debug(f"Parsed Victory store: {store_data['store_id']} - {store_data['store_name']}")
                    
                except Exception as e:
                    logger.warning(f"Error parsing Victory store element: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing Victory store XML: {e}")
            
        logger.info(f"Successfully parsed {len(stores)} Victory stores")
        return stores
    
    def parse_price_data(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parse Victory price XML format"""
        prices = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Get store info from root
            store_id = None
            for field in ['StoreID', 'StoreId', 'STOREID']:
                elem = root.find(f'.//{field}')
                if elem is not None and elem.text:
                    store_id = elem.text.strip()
                    break
            
            if not store_id:
                logger.warning("No store ID found in Victory price file")
                return prices
            
            # Find products
            products = root.findall('.//Product')
            if not products:
                products = root.findall('.//Item')
                
            logger.info(f"Found {len(products)} products in Victory price file for store {store_id}")
            
            for product in products:
                try:
                    # Get barcode
                    barcode = None
                    for field in ['ItemCode', 'Barcode', 'ProductCode']:
                        elem = product.find(field)
                        if elem is not None and elem.text:
                            barcode = elem.text.strip()
                            break
                    
                    if not barcode:
                        continue
                    
                    # Get name
                    name = None
                    for field in ['ItemName', 'ProductName', 'Name']:
                        elem = product.find(field)
                        if elem is not None and elem.text:
                            name = elem.text.strip()
                            break
                    
                    # Get price
                    price = None
                    for field in ['ItemPrice', 'Price', 'UnitPrice']:
                        elem = product.find(field)
                        if elem is not None and elem.text:
                            try:
                                price = float(elem.text.strip())
                                break
                            except ValueError:
                                continue
                    
                    if price is None or price <= 0:
                        continue
                    
                    price_data = {
                        'store_id': store_id,
                        'barcode': barcode,
                        'name': name or f"Product {barcode}",
                        'price': price
                    }
                    
                    prices.append(price_data)
                    
                except Exception as e:
                    logger.debug(f"Error parsing Victory product: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing Victory price XML: {e}")
            
        logger.info(f"Successfully parsed {len(prices)} prices from Victory")
        return prices