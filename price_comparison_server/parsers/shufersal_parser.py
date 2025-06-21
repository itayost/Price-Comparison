# price_comparison_server/parsers/shufersal_parser.py

import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from .base_parser import BaseChainParser
import logging

logger = logging.getLogger(__name__)


class ShufersalParser(BaseChainParser):
    """Parser for Shufersal chain data"""
    
    def __init__(self):
        super().__init__('shufersal', '7290027600007')
        self.base_url = 'https://prices.shufersal.co.il'
        self.stores_list_url = 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=5'
        self.prices_list_url = 'https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=2'
        
    def get_store_file_urls(self) -> List[str]:
        """Get Shufersal store file URLs"""
        return self.scrape_file_list(
            self.stores_list_url,
            {'tag': 'a', 'attrs': {'text': 'לחץ להורדה'}},
            'StoresFull'
        )
    
    def get_price_file_urls(self) -> List[str]:
        """Get Shufersal price file URLs"""
        return self.scrape_file_list(
            self.prices_list_url,
            {'tag': 'a', 'attrs': {'text': 'לחץ להורדה'}},
            'PriceFull'
        )
    
    def parse_store_data(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parse Shufersal store XML format"""
        stores = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Get chain info from root
            chain_id = root.find('.//ChainID').text if root.find('.//ChainID') is not None else self.chain_id
            
            # Parse each store
            for store in root.findall('.//Store'):
                try:
                    store_id = store.find('StoreID').text if store.find('StoreID') is not None else None
                    sub_chain_id = store.find('SubChainID').text if store.find('SubChainID') is not None else '001'
                    
                    if not store_id:
                        continue
                        
                    store_data = {
                        'chain_id': chain_id,
                        'store_id': store_id,
                        'sub_chain_id': sub_chain_id,
                        'full_store_id': f"{chain_id}-{sub_chain_id}-{store_id}",
                        'store_name': store.find('StoreName').text if store.find('StoreName') is not None else None,
                        'address': store.find('Address').text if store.find('Address') is not None else None,
                        'city': store.find('City').text if store.find('City') is not None else None,
                        'store_type': store.find('StoreType').text if store.find('StoreType') is not None else None,
                    }
                    
                    # Clean city name
                    if store_data['city']:
                        store_data['city'] = store_data['city'].strip()
                        
                    stores.append(store_data)
                    
                except Exception as e:
                    logger.warning(f"Error parsing Shufersal store: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing Shufersal store XML: {e}")
            
        return stores
    
    def parse_price_data(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parse Shufersal price XML format"""
        prices = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Get store info
            chain_id = root.find('ChainId').text if root.find('ChainId') is not None else None
            sub_chain_id = root.find('SubChainId').text if root.find('SubChainId') is not None else None
            store_id = root.find('StoreId').text if root.find('StoreId') is not None else None
            
            if not all([chain_id, store_id]):
                logger.error("Missing store identification in price file")
                return prices
                
            full_store_id = f"{chain_id}-{sub_chain_id}-{store_id}"
            
            # Parse each item
            for item in root.findall('.//Item'):
                try:
                    item_code = item.find('ItemCode').text if item.find('ItemCode') is not None else None
                    item_name = item.find('ItemName').text if item.find('ItemName') is not None else None
                    item_price = item.find('ItemPrice').text if item.find('ItemPrice') is not None else None
                    
                    if not all([item_code, item_name, item_price]):
                        continue
                    
                    # Skip items with invalid prices
                    try:
                        price_float = float(item_price)
                        if price_float <= 0:
                            continue
                    except:
                        continue
                    
                    price_data = {
                        'store_id': store_id,
                        'full_store_id': full_store_id,
                        'barcode': item_code,
                        'name': item_name.strip(),
                        'price': price_float
                    }
                    
                    prices.append(price_data)
                    
                except Exception as e:
                    logger.warning(f"Error parsing Shufersal item: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing Shufersal price XML: {e}")
            
        return prices