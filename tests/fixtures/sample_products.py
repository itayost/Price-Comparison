"""
Sample product data utilities for testing.

This module uses the actual XML parsers to create realistic test data
from the sample XML files.
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime

from parsers.shufersal_parser import ShufersalParser
from parsers.victory_parser import VictoryParser
from tests.fixtures.sample_xmls import (
    SHUFERSAL_STORES_XML,
    SHUFERSAL_PRICES_XML,
    VICTORY_STORES_XML,
    VICTORY_PRICES_XML
)


def get_parsed_shufersal_data() -> Tuple[List[Dict], List[Dict]]:
    """Parse Shufersal sample data and return stores and prices"""
    parser = ShufersalParser()
    
    stores = parser.parse_store_data(SHUFERSAL_STORES_XML.encode('utf-8'))
    prices = parser.parse_price_data(SHUFERSAL_PRICES_XML.encode('utf-8'))
    
    return stores, prices


def get_parsed_victory_data() -> Tuple[List[Dict], List[Dict]]:
    """Parse Victory sample data and return stores and prices"""
    parser = VictoryParser()
    
    stores = parser.parse_store_data(VICTORY_STORES_XML.encode('utf-8'))
    prices = parser.parse_price_data(VICTORY_PRICES_XML.encode('utf-8'))
    
    return stores, prices


def create_test_database_data(db_session):
    """
    Create complete test data in the database using parsed XML data.
    
    This is a more comprehensive version of the fixtures in conftest.py
    that uses actual parsed data.
    """
    from database.new_models import Chain, Branch, ChainProduct, BranchPrice
    
    # Create chains
    chains = {
        'shufersal': Chain(name='shufersal', display_name='שופרסל'),
        'victory': Chain(name='victory', display_name='ויקטורי')
    }
    
    db_session.add_all(chains.values())
    db_session.commit()
    
    # Parse actual XML data
    shufersal_stores, shufersal_prices = get_parsed_shufersal_data()
    victory_stores, victory_prices = get_parsed_victory_data()
    
    # Create branches from parsed store data
    branches = {}
    
    # Shufersal branches
    for store_data in shufersal_stores[:2]:  # Use first 2 stores
        branch = Branch(
            chain_id=chains['shufersal'].chain_id,
            store_id=store_data['store_id'],
            name=store_data['name'],
            address=store_data['address'],
            city=store_data['city']
        )
        branches[f"shufersal_{store_data['store_id']}"] = branch
    
    # Victory branches
    for store_data in victory_stores[:2]:  # Use first 2 stores
        branch = Branch(
            chain_id=chains['victory'].chain_id,
            store_id=store_data['store_id'],
            name=store_data['name'],
            address=store_data['address'],
            city=store_data['city']
        )
        branches[f"victory_{store_data['store_id']}"] = branch
    
    db_session.add_all(branches.values())
    db_session.commit()
    
    # Create products from parsed price data
    products = {}
    
    # Track unique products by barcode to avoid duplicates
    seen_products = {}
    
    # Shufersal products
    for price_data in shufersal_prices:
        barcode = price_data['barcode']
        if barcode not in seen_products:
            product = ChainProduct(
                chain_id=chains['shufersal'].chain_id,
                barcode=barcode,
                name=price_data['name']
            )
            products[f"shufersal_{barcode}"] = product
            seen_products[barcode] = {'shufersal': product}
        
    # Victory products (may have same barcode, different name)
    for price_data in victory_prices:
        barcode = price_data['barcode']
        if barcode not in seen_products:
            seen_products[barcode] = {}
        
        if 'victory' not in seen_products[barcode]:
            product = ChainProduct(
                chain_id=chains['victory'].chain_id,
                barcode=barcode,
                name=price_data['name']
            )
            products[f"victory_{barcode}"] = product
            seen_products[barcode]['victory'] = product
    
    db_session.add_all(products.values())
    db_session.commit()
    
    # Create prices for products at branches
    prices = []
    
    # Shufersal prices
    for price_data in shufersal_prices:
        barcode = price_data['barcode']
        store_id = price_data['store_id']
        
        # Find the product and branch
        product_key = f"shufersal_{barcode}"
        branch_key = f"shufersal_{store_id}"
        
        if product_key in products and branch_key in branches:
            price = BranchPrice(
                chain_product_id=products[product_key].chain_product_id,
                branch_id=branches[branch_key].branch_id,
                price=price_data['price'],
                last_updated=datetime.utcnow()
            )
            prices.append(price)
    
    # Victory prices
    for price_data in victory_prices:
        barcode = price_data['barcode']
        store_id = price_data['store_id']
        
        # Find the product and branch
        product_key = f"victory_{barcode}"
        branch_key = f"victory_{store_id}"
        
        if product_key in products and branch_key in branches:
            price = BranchPrice(
                chain_product_id=products[product_key].chain_product_id,
                branch_id=branches[branch_key].branch_id,
                price=price_data['price'],
                last_updated=datetime.utcnow()
            )
            prices.append(price)
    
    db_session.add_all(prices)
    db_session.commit()
    
    return {
        'chains': chains,
        'branches': branches,
        'products': products,
        'prices': prices
    }


# Common test cart items based on actual products in the XML
SAMPLE_CART_ITEMS = [
    {
        'barcode': '7290000000001',
        'quantity': 2,
        'name': 'חלב טרה 3%'
    },
    {
        'barcode': '7290000000002',
        'quantity': 1,
        'name': 'לחם אחיד'
    },
    {
        'barcode': '7290000000003',
        'quantity': 1,
        'name': 'ביצים L'
    }
]


def create_cart_comparison_request(city: str = 'תל אביב', items: List[Dict] = None):
    """Create a cart comparison request for testing"""
    if items is None:
        items = SAMPLE_CART_ITEMS
    
    return {
        'city': city,
        'items': items
    }


def get_expected_cart_prices():
    """Get expected prices for the sample cart based on XML data"""
    # Parse the actual prices from XML
    _, shufersal_prices = get_parsed_shufersal_data()
    _, victory_prices = get_parsed_victory_data()
    
    # Create lookup dictionaries
    shufersal_price_map = {p['barcode']: p['price'] for p in shufersal_prices}
    victory_price_map = {p['barcode']: p['price'] for p in victory_prices}
    
    # Calculate expected totals for sample cart
    shufersal_total = 0
    victory_total = 0
    
    for item in SAMPLE_CART_ITEMS:
        barcode = item['barcode']
        quantity = item['quantity']
        
        if barcode in shufersal_price_map:
            shufersal_total += shufersal_price_map[barcode] * quantity
        
        if barcode in victory_price_map:
            victory_total += victory_price_map[barcode] * quantity
    
    return {
        'shufersal': shufersal_total,
        'victory': victory_total,
        'cheapest': 'shufersal' if shufersal_total < victory_total else 'victory'
    }


def get_product_search_expectations():
    """Get expected results for product search tests"""
    _, shufersal_prices = get_parsed_shufersal_data()
    
    # Group products by common search terms
    milk_products = [p for p in shufersal_prices if 'חלב' in p['name']]
    bread_products = [p for p in shufersal_prices if 'לחם' in p['name']]
    
    return {
        'חלב': milk_products,
        'לחם': bread_products
    }


# Helper functions for test assertions
def assert_valid_product_response(product_data: Dict):
    """Assert that a product response has all required fields"""
    assert 'barcode' in product_data
    assert 'name' in product_data
    assert 'prices_by_store' in product_data or 'price' in product_data


def assert_valid_cart_comparison(comparison_data: Dict):
    """Assert that a cart comparison response has all required fields"""
    assert 'success' in comparison_data
    assert 'total_items' in comparison_data
    assert 'cheapest_store' in comparison_data
    assert 'all_stores' in comparison_data


def assert_valid_store_result(store_data: Dict):
    """Assert that a store result has all required fields"""
    required_fields = [
        'chain_name', 'branch_name', 'address', 'city',
        'total_price', 'available_items', 'missing_items'
    ]
    for field in required_fields:
        assert field in store_data
