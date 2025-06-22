#!/usr/bin/env python3
# price_comparison_server/scripts/test_cart_comparison.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db
from services.cart_service import CartComparisonService, CartItem
from database.new_models import ChainProduct, Branch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_cart_comparison():
    """Test the cart comparison functionality"""
    
    with get_db() as db:
        service = CartComparisonService(db)
        
        # 1. First, let's see what products we have
        logger.info("=== Available Products Sample ===")
        sample_products = db.query(ChainProduct).limit(10).all()
        
        if not sample_products:
            logger.error("No products found in database! Run import scripts first.")
            return
        
        logger.info(f"Found {len(sample_products)} products. Sample:")
        for product in sample_products[:5]:
            logger.info(f"  - {product.barcode}: {product.name}")
        
        # 2. Check available cities
        logger.info("\n=== Available Cities ===")
        cities = db.query(Branch.city).distinct().limit(10).all()
        logger.info(f"Found {len(cities)} cities. Sample:")
        for city in cities[:5]:
            logger.info(f"  - {city[0]}")
        
        if not cities:
            logger.error("No cities found! Import stores first.")
            return
        
        # 3. Create a test cart with real products
        test_city = cities[0][0]  # Use first available city
        logger.info(f"\n=== Testing Cart Comparison in {test_city} ===")
        
        # Create cart with first 3 products
        cart_items = []
        for i, product in enumerate(sample_products[:3]):
            cart_items.append(CartItem(
                barcode=product.barcode,
                quantity=i + 1,  # 1, 2, 3
                name=product.name
            ))
        
        logger.info(f"Cart items:")
        for item in cart_items:
            logger.info(f"  - {item.barcode}: {item.name} x{item.quantity}")
        
        # 4. Run comparison
        logger.info(f"\nComparing prices in {test_city}...")
        comparison = service.compare_cart(cart_items, test_city)
        
        # 5. Show results
        logger.info(f"\n=== Comparison Results ===")
        logger.info(f"Total stores compared: {len(comparison.all_stores)}")
        
        if comparison.cheapest_store:
            logger.info(f"\n🏆 Cheapest Store:")
            logger.info(f"  Chain: {comparison.cheapest_store.chain_display_name}")
            logger.info(f"  Branch: {comparison.cheapest_store.branch_name}")
            logger.info(f"  Address: {comparison.cheapest_store.branch_address}")
            logger.info(f"  Total Price: ₪{comparison.cheapest_store.total_price:.2f}")
            logger.info(f"  Available Items: {comparison.cheapest_store.available_items}/{comparison.total_items}")
            
            logger.info(f"\n  Item Breakdown:")
            for item in comparison.cheapest_store.items_detail:
                if item['available']:
                    logger.info(f"    ✓ {item['name']}: ₪{item['unit_price']:.2f} x {item['quantity']} = ₪{item['total_price']:.2f}")
                else:
                    logger.info(f"    ✗ {item['name']}: Not available")
        
        # 6. Show top 3 stores
        logger.info(f"\n📊 Top 3 Cheapest Stores:")
        for i, store in enumerate(comparison.all_stores[:3], 1):
            logger.info(f"\n  {i}. {store.chain_display_name} - {store.branch_name}")
            logger.info(f"     Total: ₪{store.total_price:.2f} ({store.available_items}/{comparison.total_items} items)")
        
        # 7. Test product search
        logger.info(f"\n=== Testing Product Search ===")
        search_query = "חלב"  # Search for milk
        logger.info(f"Searching for: {search_query}")
        
        results = service.search_products(search_query, limit=5)
        logger.info(f"Found {len(results)} products:")
        for result in results:
            logger.info(f"  - {result['barcode']}: {result['name']} (available in {result['availability']} stores)")


def test_api_format():
    """Test the API request/response format"""
    logger.info("\n=== API Format Example ===")
    
    sample_request = {
        "city": "תל אביב",
        "items": [
            {"barcode": "7290000000001", "quantity": 2, "name": "חלב 3%"},
            {"barcode": "7290000000002", "quantity": 1, "name": "לחם"},
            {"barcode": "7290000000003", "quantity": 3, "name": "ביצים"}
        ]
    }
    
    logger.info("Sample API Request:")
    import json
    logger.info(json.dumps(sample_request, ensure_ascii=False, indent=2))
    
    logger.info("\nExpected Response Structure:")
    sample_response = {
        "success": True,
        "total_items": 3,
        "city": "תל אביב",
        "cheapest_store": {
            "branch_id": 123,
            "branch_name": "שופרסל דיל רמת גן",
            "branch_address": "ביאליק 15",
            "city": "רמת גן",
            "chain_name": "shufersal",
            "chain_display_name": "שופרסל",
            "available_items": 3,
            "missing_items": 0,
            "total_price": 45.50,
            "items_detail": [
                {
                    "barcode": "7290000000001",
                    "name": "חלב 3%",
                    "quantity": 2,
                    "unit_price": 6.50,
                    "total_price": 13.00,
                    "available": True
                }
            ]
        },
        "all_stores": ["... list of all stores ..."],
        "comparison_time": "2024-01-15T10:30:00"
    }
    
    logger.info(json.dumps(sample_response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    logger.info("Starting Cart Comparison Test\n")
    
    try:
        test_cart_comparison()
        test_api_format()
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
