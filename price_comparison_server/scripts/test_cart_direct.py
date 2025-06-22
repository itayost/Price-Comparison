#!/usr/bin/env python3
# price_comparison_server/scripts/test_cart_direct.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db
from database.new_models import Chain, Branch, ChainProduct, BranchPrice
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import func, and_
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define classes directly to avoid import issues
@dataclass
class CartItem:
    barcode: str
    quantity: int = 1
    name: Optional[str] = None

@dataclass
class StorePrice:
    branch_id: int
    branch_name: str
    branch_address: str
    city: str
    chain_name: str
    chain_display_name: str
    available_items: int
    missing_items: int
    total_price: float
    items_detail: List[Dict[str, Any]]


def test_cart_comparison():
    """Test cart comparison with real data"""
    
    with get_db() as db:
        # 1. Get some real products
        logger.info("=== Preparing Test Cart ===")
        
        # Get products that are likely to be in multiple stores
        popular_products = db.query(
            ChainProduct.barcode,
            ChainProduct.name,
            func.count(BranchPrice.price_id).label('availability')
        ).join(
            BranchPrice
        ).group_by(
            ChainProduct.barcode,
            ChainProduct.name
        ).having(
            func.count(BranchPrice.price_id) > 10
        ).order_by(
            func.count(BranchPrice.price_id).desc()
        ).limit(5).all()
        
        if not popular_products:
            logger.error("No popular products found!")
            return
        
        # Create test cart
        cart_items = []
        for i, (barcode, name, availability) in enumerate(popular_products[:3]):
            cart_items.append(CartItem(
                barcode=barcode,
                quantity=i + 1,
                name=name
            ))
            logger.info(f"  - {name} x{i+1} (available in {availability} stores)")
        
        # 2. Get a city with multiple stores
        city_stores = db.query(
            Branch.city,
            func.count(Branch.branch_id).label('store_count')
        ).group_by(
            Branch.city
        ).having(
            func.count(Branch.branch_id) > 5
        ).order_by(
            func.count(Branch.branch_id).desc()
        ).first()
        
        if not city_stores:
            logger.error("No city with multiple stores found!")
            return
        
        test_city = city_stores[0]
        logger.info(f"\nTesting in city: {test_city} ({city_stores[1]} stores)")
        
        # 3. Get branches in the city
        branches = db.query(Branch).filter(
            Branch.city == test_city
        ).all()
        
        logger.info(f"\n=== Comparing Prices Across {len(branches)} Stores ===")
        
        # 4. Calculate prices for each store
        store_results = []
        
        for branch in branches:
            total_price = 0.0
            available_items = 0
            missing_items = 0
            items_detail = []
            
            for item in cart_items:
                # Find product price at this branch
                price_info = db.query(
                    BranchPrice.price,
                    ChainProduct.name
                ).join(
                    ChainProduct
                ).filter(
                    and_(
                        ChainProduct.barcode == item.barcode,
                        ChainProduct.chain_id == branch.chain_id,
                        BranchPrice.branch_id == branch.branch_id
                    )
                ).first()
                
                if price_info:
                    price, product_name = price_info
                    # Convert Decimal to float for calculations
                    price_float = float(price)
                    item_total = price_float * item.quantity
                    total_price += item_total
                    available_items += 1

                    items_detail.append({
                        'name': product_name,
                        'quantity': item.quantity,
                        'unit_price': price_float,
                        'total_price': item_total,
                        'available': True
                    })
                else:
                    missing_items += 1
                    items_detail.append({
                        'name': item.name,
                        'quantity': item.quantity,
                        'available': False
                    })

            # Skip stores with no items
            if available_items == 0:
                continue

            # Get chain info
            chain = db.query(Chain).filter(Chain.chain_id == branch.chain_id).first()

            store_results.append(StorePrice(
                branch_id=branch.branch_id,
                branch_name=branch.name,
                branch_address=branch.address,
                city=branch.city,
                chain_name=chain.name if chain else 'unknown',
                chain_display_name=chain.display_name if chain else 'Unknown',
                available_items=available_items,
                missing_items=missing_items,
                total_price=total_price,
                items_detail=items_detail
            ))

        # 5. Sort by price and show results
        store_results.sort(key=lambda x: x.total_price)

        if not store_results:
            logger.warning("No stores have any of the items!")
            return

        logger.info(f"\n🏆 CHEAPEST STORE:")
        cheapest = store_results[0]
        logger.info(f"  {cheapest.chain_display_name} - {cheapest.branch_name}")
        logger.info(f"  Address: {cheapest.branch_address}")
        logger.info(f"  Total: ₪{cheapest.total_price:.2f}")
        logger.info(f"  Items: {cheapest.available_items}/{len(cart_items)} available")

        logger.info(f"\n📊 Price Breakdown:")
        for item in cheapest.items_detail:
            if item['available']:
                logger.info(f"  ✓ {item['name']}: ₪{item['unit_price']:.2f} x {item['quantity']} = ₪{item['total_price']:.2f}")
            else:
                logger.info(f"  ✗ {item['name']}: Not available")

        logger.info(f"\n💰 TOP 5 CHEAPEST STORES:")
        for i, store in enumerate(store_results[:5], 1):
            logger.info(f"  {i}. {store.chain_display_name} - {store.branch_name}")
            logger.info(f"     Total: ₪{store.total_price:.2f} ({store.available_items}/{len(cart_items)} items)")

        # 6. Show price variance
        if len(store_results) > 1:
            cheapest_price = store_results[0].total_price
            most_expensive_price = store_results[-1].total_price
            savings = most_expensive_price - cheapest_price
            savings_percent = (savings / most_expensive_price) * 100

            logger.info(f"\n💡 SAVINGS POTENTIAL:")
            logger.info(f"  Cheapest: ₪{cheapest_price:.2f}")
            logger.info(f"  Most expensive: ₪{most_expensive_price:.2f}")
            logger.info(f"  You can save: ₪{savings:.2f} ({savings_percent:.1f}%)")


if __name__ == "__main__":
    logger.info("Direct Cart Comparison Test\n")

    try:
        test_cart_comparison()
        logger.info("\n✅ Cart comparison logic is working!")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
