#!/usr/bin/env python3
# price_comparison_server/scripts/test_xml_parsing.py

import xml.etree.ElementTree as ET
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_shufersal_xml():
    """Test parsing Shufersal XML structure"""
    logger.info("=== Testing Shufersal XML Parsing ===")
    
    # Read the uploaded Shufersal file
    try:
        with open('Stores7290027600007-000-202506210201.xml', 'rb') as f:
            xml_content = f.read()
        
        root = ET.fromstring(xml_content)
        
        # Log root structure
        logger.info(f"Root tag: {root.tag}")
        
        # Find chain ID
        chain_id = root.find('.//CHAINID')
        if chain_id is not None:
            logger.info(f"Chain ID: {chain_id.text}")
        
        # Find stores
        stores = root.findall('.//STORE')
        logger.info(f"Found {len(stores)} stores")
        
        # Parse first few stores
        parsed_stores = []
        for i, store in enumerate(stores[:5]):
            store_data = {
                'store_id': store.find('STOREID').text if store.find('STOREID') is not None else None,
                'store_name': store.find('STORENAME').text if store.find('STORENAME') is not None else None,
                'city': store.find('CITY').text if store.find('CITY') is not None else None,
                'address': store.find('ADDRESS').text if store.find('ADDRESS') is not None else None,
            }
            parsed_stores.append(store_data)
            logger.info(f"Store {i+1}: ID={store_data['store_id']}, Name={store_data['store_name']}, City={store_data['city']}")
        
        return len(stores)
        
    except Exception as e:
        logger.error(f"Error parsing Shufersal XML: {e}")
        return 0


def test_victory_xml():
    """Test parsing Victory XML structure"""
    logger.info("\n=== Testing Victory XML Parsing ===")
    
    # Read the uploaded Victory file
    try:
        with open('StoresFull7290696200003-000-202506210600-000.xml', 'rb') as f:
            xml_content = f.read()
        
        root = ET.fromstring(xml_content)
        
        # Log root structure
        logger.info(f"Root tag: {root.tag}")
        
        # Find branches container
        branches = root.find('.//Branches')
        if branches is None:
            logger.error("No Branches element found")
            return 0
        
        # Find all Branch elements
        stores = branches.findall('Branch')
        logger.info(f"Found {len(stores)} stores")
        
        # Parse first few stores
        parsed_stores = []
        for i, store in enumerate(stores[:5]):
            store_data = {
                'store_id': store.find('StoreID').text if store.find('StoreID') is not None else None,
                'store_name': store.find('StoreName').text if store.find('StoreName') is not None else None,
                'city': store.find('City').text if store.find('City') is not None else None,
                'address': store.find('Address').text if store.find('Address') is not None else None,
            }
            parsed_stores.append(store_data)
            logger.info(f"Store {i+1}: ID={store_data['store_id']}, Name={store_data['store_name']}, City={store_data['city']}")
        
        return len(stores)
        
    except Exception as e:
        logger.error(f"Error parsing Victory XML: {e}")
        return 0


def main():
    """Run tests"""
    shufersal_count = test_shufersal_xml()
    victory_count = test_victory_xml()
    
    logger.info("\n=== Summary ===")
    logger.info(f"Shufersal stores found: {shufersal_count}")
    logger.info(f"Victory stores found: {victory_count}")
    
    if shufersal_count > 0 and victory_count > 0:
        logger.info("\n✅ Both XML formats parsed successfully!")
        logger.info("You can now update your parsers with the fixed versions.")


if __name__ == "__main__":
    main()