# price_comparison_server/parsers/shufersal_parser.py

import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from .base_parser import BaseChainParser
import logging
import requests
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


class ShufersalParser(BaseChainParser):
    """Parser for Shufersal chain data with pagination support"""

    def __init__(self):
        super().__init__('shufersal', '7290027600007')
        self.base_url = 'https://prices.shufersal.co.il'
        self.stores_list_url = 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=5'
        self.prices_list_url = 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=2&storeId=0&page='

    def get_store_file_urls(self) -> List[str]:
        """Get Shufersal store file URLs"""
        return self.scrape_file_list(
            self.stores_list_url,
            {'tag': 'a', 'text': 'לחץ להורדה'},
            'Stores'
        )

    def get_price_file_urls(self) -> List[str]:
        """Get Shufersal price file URLs with pagination"""
        logger.info("Getting Shufersal price file URLs...")

        # First, find the last page number
        last_page = self._get_last_page_number()
        logger.info(f"Found {last_page} pages of price files")

        all_urls = []
        seen_files = set()

        # Process all pages
        for page in range(1, last_page + 1):
            logger.info(f"Processing page {page}/{last_page}")
            page_url = f"{self.prices_list_url}{page}"

            # Use the base parser's scrape_file_list method
            urls = self.scrape_file_list(
                page_url,
                {'tag': 'a', 'text': 'לחץ להורדה'},
                'Price'
            )

            # Add unique files only
            for url in urls:
                filename = url.split('/')[-1]
                if filename not in seen_files:
                    seen_files.add(filename)
                    all_urls.append(url)

        logger.info(f"Found {len(all_urls)} unique price files")
        return all_urls

    def _get_last_page_number(self) -> int:
        """Find the last page number from the >> button"""
        try:
            # Check first page
            response = requests.get(f"{self.prices_list_url}1", timeout=30)
            if response.status_code != 200:
                return 1

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find >> link
            for link in soup.find_all('a'):
                if link.get_text(strip=True) == '>>':
                    href = link.get('href', '')
                    match = re.search(r'page=(\d+)', href)
                    if match:
                        return int(match.group(1))

            logger.warning("Could not find >> button, defaulting to 1 page")
            return 1

        except Exception as e:
            logger.error(f"Error finding last page: {e}")
            return 1

    def parse_store_data(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parse Shufersal store XML format"""
        stores = []

        try:
            root = ET.fromstring(xml_content)

            # Find all stores
            store_elements = root.findall('.//STORE')
            logger.info(f"Found {len(store_elements)} stores in file")

            for store in store_elements:
                try:
                    # Get store ID and remove leading zeros
                    store_id_elem = store.find('STOREID')
                    if store_id_elem is None or not store_id_elem.text:
                        continue

                    store_id = str(int(store_id_elem.text.strip()))

                    store_data = {
                        'store_id': store_id,
                        'store_name': self._get_text(store, 'STORENAME', f"Store {store_id}"),
                        'address': self._get_text(store, 'ADDRESS', ''),
                        'city': self._get_text(store, 'CITY', ''),
                    }

                    stores.append(store_data)

                except Exception as e:
                    logger.warning(f"Error parsing store element: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing store XML: {e}")

        logger.info(f"Successfully parsed {len(stores)} stores")
        return stores

    def parse_price_data(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parse Shufersal price XML format"""
        prices = []

        try:
            root = ET.fromstring(xml_content)

            # Get store ID
            store_id = None
            for field in ['StoreId', 'StoreID', 'STOREID']:
                elem = root.find(f'.//{field}')
                if elem is not None and elem.text:
                    store_id = str(int(elem.text.strip()))  # Remove leading zeros
                    break

            if not store_id:
                logger.warning("No store ID found in price file")
                return prices

            # Find products
            products = root.findall('.//Product')
            if not products:
                products = root.findall('.//Item')
            if not products:
                products = root.findall('.//PRODUCT')

            logger.debug(f"Found {len(products)} products for store {store_id}")

            for product in products:
                try:
                    # Get barcode
                    barcode = None
                    for field in ['ItemCode', 'Barcode', 'ITEMCODE']:
                        elem = product.find(field)
                        if elem is not None and elem.text:
                            barcode = elem.text.strip()
                            break

                    if not barcode:
                        continue

                    # Get name
                    name = None
                    for field in ['ItemName', 'ProductName', 'ITEMNAME']:
                        elem = product.find(field)
                        if elem is not None and elem.text:
                            name = elem.text.strip()
                            break

                    # Get price
                    price = None
                    for field in ['ItemPrice', 'Price', 'ITEMPRICE']:
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
                    logger.debug(f"Error parsing product: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing price XML: {e}")

        logger.info(f"Successfully parsed {len(prices)} prices")
        return prices

    def _get_text(self, element, tag: str, default: str = '') -> str:
        """Safely get text from XML element"""
        elem = element.find(tag)
        if elem is not None and elem.text:
            return elem.text.strip()
        return default
