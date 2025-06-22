# price_comparison_server/parsers/shufersal_parser.py

import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from .base_parser import BaseChainParser
import logging

logger = logging.getLogger(__name__)


class ShufersalParser(BaseChainParser):
    """Parser for Shufersal chain data - Fixed for actual XML structure"""

    def __init__(self):
        super().__init__('shufersal', '7290027600007')
        self.base_url = 'https://prices.shufersal.co.il'
        self.stores_list_url = 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=5'
        self.prices_list_url = 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=2'

    def get_store_file_urls(self) -> List[str]:
        """Get Shufersal store file URLs"""
        return self.scrape_file_list(
            self.stores_list_url,
            {'tag': 'a', 'text': 'לחץ להורדה'},  # Fixed: use text directly
            'Stores'  # Look for Stores in URL
        )

    def get_price_file_urls(self) -> List[str]:
        """Get Shufersal price file URLs"""
        return self.scrape_file_list(
            self.prices_list_url,
            {'tag': 'a', 'text': 'לחץ להורדה'},
            'Price'
        )

    def parse_store_data(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parse Shufersal store XML format - Fixed for SAP/ABAP format"""
        stores = []

        try:
            # Parse XML with namespace handling
            root = ET.fromstring(xml_content)

            # Define namespace
            ns = {'asx': 'http://www.sap.com/abapxml'}

            # Get chain ID from root
            chain_id_elem = root.find('.//CHAINID', ns)
            if chain_id_elem is None:
                chain_id_elem = root.find('.//CHAINID')
            chain_id = chain_id_elem.text if chain_id_elem is not None else self.chain_id

            # Find all stores - try with and without namespace
            store_elements = root.findall('.//STORE', ns)
            if not store_elements:
                store_elements = root.findall('.//STORE')

            logger.info(f"Found {len(store_elements)} store elements in Shufersal XML")

            for store in store_elements:
                try:
                    # Extract store data - Shufersal uses uppercase field names
                    store_id = store.find('STOREID')
                    if store_id is None or not store_id.text:
                        continue

                    store_data = {
                        'chain_id': chain_id,
                        'store_id': str(int(store_id.text.strip())),  # Convert to int then back to string to remove leading zeros
                        'sub_chain_id': store.find('SUBCHAINID').text if store.find('SUBCHAINID') is not None else '1',
                        'store_name': store.find('STORENAME').text if store.find('STORENAME') is not None else f"Store {store_id.text}",
                        'address': store.find('ADDRESS').text if store.find('ADDRESS') is not None else "Unknown",
                        'city': store.find('CITY').text.strip() if store.find('CITY') is not None and store.find('CITY').text else "Unknown",
                        'store_type': store.find('STORETYPE').text if store.find('STORETYPE') is not None else None,
                    }

                    # Create full store ID
                    store_data['full_store_id'] = f"{chain_id}-{store_data['sub_chain_id']}-{store_data['store_id']}"

                    stores.append(store_data)
                    logger.debug(f"Parsed Shufersal store: {store_data['store_id']} - {store_data['store_name']}")

                except Exception as e:
                    logger.warning(f"Error parsing Shufersal store element: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing Shufersal store XML: {e}")

        logger.info(f"Successfully parsed {len(stores)} Shufersal stores")
        return stores

    def parse_price_data(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parse Shufersal price XML format"""
        prices = []

        try:
            root = ET.fromstring(xml_content)

            # Get store info - Shufersal format
            store_id = None
            for field in ['StoreId', 'StoreID', 'STOREID']:
                elem = root.find(f'.//{field}')
                if elem is not None and elem.text:
                    store_id = str(int(elem.text.strip()))  # Convert to int to remove leading zeros
                    break

            if not store_id:
                logger.warning("No store ID found in Shufersal price file")
                return prices

            # Find products - try different paths
            products = root.findall('.//Product')
            if not products:
                products = root.findall('.//Item')
            if not products:
                products = root.findall('.//PRODUCT')

            logger.info(f"Found {len(products)} products in Shufersal price file for store {store_id}")

            for product in products:
                try:
                    # Get barcode
                    barcode = None
                    for field in ['ItemCode', 'Barcode', 'ITEMCODE', 'BARCODE']:
                        elem = product.find(field)
                        if elem is not None and elem.text:
                            barcode = elem.text.strip()
                            break

                    if not barcode:
                        continue

                    # Get name
                    name = None
                    for field in ['ItemName', 'ProductName', 'ITEMNAME', 'PRODUCTNAME']:
                        elem = product.find(field)
                        if elem is not None and elem.text:
                            name = elem.text.strip()
                            break

                    # Get price
                    price = None
                    for field in ['ItemPrice', 'Price', 'ITEMPRICE', 'PRICE']:
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
                    logger.debug(f"Error parsing Shufersal product: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing Shufersal price XML: {e}")

        logger.info(f"Successfully parsed {len(prices)} prices from Shufersal")
        return prices
