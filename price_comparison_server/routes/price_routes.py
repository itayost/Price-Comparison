from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import os
import sys
from typing import List, Dict, Any, Set, Optional
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path if needed
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import models and utilities
from models.data_models import Price as PriceModel, CartRequest, CartItem
from database.connection import get_db_session
from database.models import Store, Price, User, Cart, CartItem as DBCartItem

# Import the new Oracle-compatible search service
from services.oracle_search_service import (
    search_products_by_name_and_city_with_db,
    calculate_cheapest_cart,
    parse_query
)

# Create router
router = APIRouter(tags=["prices"])

# ============= Basic Price Endpoints =============

@router.get("/prices/{chain_name}/store/{snif_key}", response_model=List[PriceModel])
def get_prices_by_store(chain_name: str, snif_key: str, db: Session = Depends(get_db_session)):
    """Get all prices for a specific store"""
    store = db.query(Store).filter(
        Store.chain == chain_name,
        Store.snif_key == snif_key
    ).first()

    if not store:
        raise HTTPException(status_code=404, detail=f"Store {snif_key} not found in {chain_name}")

    prices = db.query(Price).filter(Price.store_id == store.id).all()

    return [{
        "snif_key": store.snif_key,
        "item_code": p.item_code,
        "item_name": p.item_name,
        "item_price": p.item_price,
        "timestamp": p.timestamp.isoformat()
    } for p in prices]

@router.get("/prices/{chain_name}/item_code/{item_code}", response_model=List[PriceModel])
def get_prices_by_item_code(chain_name: str, item_code: str, db: Session = Depends(get_db_session)):
    """Get all prices for a specific item code across all stores"""
    results = db.query(Price, Store).join(Store).filter(
        Store.chain == chain_name,
        Price.item_code == item_code
    ).all()

    if not results:
        raise HTTPException(status_code=404, detail=f"Item code {item_code} not found")

    return [{
        "snif_key": store.snif_key,
        "item_code": price.item_code,
        "item_name": price.item_name,
        "item_price": price.item_price,
        "timestamp": price.timestamp.isoformat()
    } for price, store in results]

# ============= City Endpoints =============

@router.get("/cities-list")
def get_cities_list(db: Session = Depends(get_db_session)):
    """Get simple list of all cities"""
    cities = db.query(Store.city).distinct().order_by(Store.city).all()
    return [city[0] for city in cities]

@router.get("/cities-list-with-stores")
def get_cities_list_with_stores(db: Session = Depends(get_db_session)):
    """Get cities with store count information"""
    results = db.query(
        Store.city,
        Store.chain,
        func.count(Store.id).label('count')
    ).group_by(Store.city, Store.chain).all()

    cities_data = defaultdict(lambda: {'shufersal': 0, 'victory': 0})
    for city, chain, count in results:
        cities_data[city][chain] = count

    formatted_cities = []
    for city, counts in sorted(cities_data.items()):
        store_info = []
        if counts['shufersal'] > 0:
            store_info.append(f"{counts['shufersal']} shufersal")
        if counts['victory'] > 0:
            store_info.append(f"{counts['victory']} victory")
        formatted_cities.append(f"{city}: {', '.join(store_info)}")

    return formatted_cities

# ============= Search Endpoints =============

@router.get("/prices/by-item/{city}/{item_name}")
def search_products(city: str, item_name: str,
                   group_by_code: bool = Query(True),
                   limit: int = Query(50),
                   db: Session = Depends(get_db_session)):
    """
    Search for products by name in a specific city
    Now using the new Oracle-compatible search service
    """
    logger.info(f"Search request: '{item_name}' in {city}")

    try:
        # Use the new search function
        results = search_products_by_name_and_city_with_db(
            db, city, item_name, group_by_code
        )

        # Limit results
        if limit and limit < len(results):
            results = results[:limit]

        return results

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.get("/prices/identical-products/{city}/{item_name}")
def get_identical_products(city: str, item_name: str,
                          limit: int = Query(50),
                          cross_chain_only: bool = Query(False),
                          db: Session = Depends(get_db_session)):
    """
    Get identical products (by item code) across different stores

    Args:
        city: City to search in
        item_name: Product name to search for
        limit: Maximum results to return
        cross_chain_only: If True, only show products available in multiple chains
    """
    logger.info(f"Searching for identical products: '{item_name}' in {city}")

    try:
        # Use grouped search
        all_results = search_products_by_name_and_city_with_db(
            db, city, item_name, group_by_code=True
        )

        # Filter to only multi-store products
        if cross_chain_only:
            # Only products in multiple chains
            identical_products = [
                product for product in all_results
                if product.get('cross_chain', False)
            ]
        else:
            # Any product in multiple stores (same chain or different chains)
            identical_products = [
                product for product in all_results
                if product.get('multi_store', False)
            ]

        # Sort by savings potential
        identical_products.sort(key=lambda p: (
            -p.get('store_count', 1),  # More stores first
            -p.get('price_comparison', {}).get('savings', 0)  # Higher savings first
        ))

        # Limit results
        if limit:
            identical_products = identical_products[:limit]

        logger.info(f"Found {len(identical_products)} identical products")

        return identical_products

    except Exception as e:
        logger.error(f"Identical products search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

# ============= Cart Endpoints =============

@router.post("/cheapest-cart-all-chains")
def find_cheapest_cart(cart_request: CartRequest, db: Session = Depends(get_db_session)):
    """
    Find the cheapest store for a shopping cart
    Now using the new Oracle-compatible calculation
    """
    logger.info(f"Cheapest cart request for {len(cart_request.items)} items in {cart_request.city}")

    try:
        # Convert cart items to the format expected by the function
        cart_items = [
            {
                'item_name': item.item_name,
                'quantity': item.quantity
            }
            for item in cart_request.items
        ]

        # Use the new calculation function
        result = calculate_cheapest_cart(db, cart_request.city, cart_items)

        # Check for errors
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cheapest cart calculation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")

# ============= Statistics Endpoints =============

@router.get("/statistics/overview")
def get_statistics(db: Session = Depends(get_db_session)):
    """Get database statistics"""
    try:
        stats = {
            'total_stores': db.query(Store).count(),
            'total_prices': db.query(Price).count(),
            'total_cities': db.query(func.count(func.distinct(Store.city))).scalar(),
            'chains': {}
        }

        # Get stats by chain
        chain_stats = db.query(
            Store.chain,
            func.count(func.distinct(Store.id)).label('stores'),
            func.count(Price.id).label('prices')
        ).outerjoin(Price).group_by(Store.chain).all()

        for chain, stores, prices in chain_stats:
            stats['chains'][chain] = {
                'stores': stores,
                'prices': prices
            }

        return stats

    except Exception as e:
        logger.error(f"Statistics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Statistics error: {str(e)}")

# ============= Health Check =============

@router.get("/health")
def health_check(db: Session = Depends(get_db_session)):
    """Check if the price service is healthy"""
    try:
        # Test database connection
        db.execute("SELECT 1")

        # Check if we have data
        has_stores = db.query(Store).first() is not None
        has_prices = db.query(Price).first() is not None

        return {
            "status": "healthy",
            "database": "connected",
            "has_stores": has_stores,
            "has_prices": has_prices,
            "database_type": "Oracle" if os.getenv("USE_ORACLE", "false").lower() == "true" else "PostgreSQL/SQLite"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
