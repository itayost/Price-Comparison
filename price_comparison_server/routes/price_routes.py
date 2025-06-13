from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import os
import sys
from typing import List, Dict, Any, Set, Optional, Tuple
import logging
from dataclasses import dataclass
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

# Import search function for advanced product matching
from services.search_service import search_products_by_name_and_city

# Create router
router = APIRouter(tags=["prices"])


@dataclass
class StoreInventory:
    """Tracks inventory and prices for a single store"""
    chain: str
    store_id: str
    items: Dict[str, float]  # item_name -> best_price
    
    @property
    def store_key(self) -> str:
        return f"{self.chain}:{self.store_id}"
    
    def has_all_items(self, required_items: List[str]) -> bool:
        return all(item in self.items for item in required_items)
    
    def calculate_total(self, cart_items: List[CartItem]) -> float:
        total = 0.0
        for item in cart_items:
            if item.item_name in self.items:
                total += self.items[item.item_name] * item.quantity
            else:
                return float('inf')  # Missing item
        return total

@dataclass
class PriceEntry:
    """Represents a single price entry from search results"""
    chain: str
    store_id: str
    price: float
    item_name: str

# ============= Helper Functions =============

def extract_price_entries(search_result: Dict[str, Any]) -> List[PriceEntry]:
    """
    Extract price entries from both old and new format search results.
    Handles cross-chain products (with prices array) and single-chain products.
    """
    entries = []
    
    # Check for cross-chain product (new format)
    if 'prices' in search_result and isinstance(search_result['prices'], list):
        for price_info in search_result['prices']:
            chain = price_info.get('chain')
            store_id = price_info.get('store_id')
            price = price_info.get('price', 0)
            
            if chain and store_id and price > 0:
                entries.append(PriceEntry(
                    chain=chain,
                    store_id=store_id,
                    price=price,
                    item_name=search_result.get('item_name', '')
                ))
    
    # Check for single-chain product (old format)
    elif all(key in search_result for key in ['chain', 'store_id']):
        chain = search_result.get('chain')
        store_id = search_result.get('store_id')
        price = search_result.get('price', search_result.get('item_price', 0))
        
        if chain and store_id and price > 0:
            entries.append(PriceEntry(
                chain=chain,
                store_id=store_id,
                price=price,
                item_name=search_result.get('item_name', '')
            ))
    
    return entries

def get_available_cities() -> Dict[str, List[str]]:
    """Get all available cities grouped by chain"""
    cities = defaultdict(list)
    
    for chain_name, chain_path in DBS.items():
        if os.path.exists(chain_path):
            for city in os.listdir(chain_path):
                city_path = os.path.join(chain_path, city)
                if os.path.isdir(city_path):
                    cities[chain_name].append(city)
    
    return dict(cities)

# ============= Basic Price Endpoints =============

@router.get("/prices/{chain_name}/store/{snif_key}", response_model=List[PriceModel])
def get_prices_by_store(chain_name: str, snif_key: str, db: Session = Depends(get_db_session)):
    """Get all prices for a specific store"""
    # Find the store
    store = db.query(Store).filter(
        Store.chain == chain_name,
        Store.snif_key == snif_key
    ).first()

    if not store:
        raise HTTPException(status_code=404, detail=f"Store {snif_key} not found in {chain_name}")

    # Get prices for this store
    prices = db.query(Price).filter(Price.store_id == store.id).all()

    # Convert to response format
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
    # Join prices with stores to filter by chain
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
    # Query to count stores by city and chain
    results = db.query(
        Store.city,
        Store.chain,
        func.count(Store.id).label('count')
    ).group_by(Store.city, Store.chain).all()

    # Format the response
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

# ============= Search Endpoints (Temporary) =============

@router.get("/prices/by-item/{city}/{item_name}")
def search_products(city: str, item_name: str,
                   group_by_code: bool = Query(True),
                   limit: int = Query(50),
                   db: Session = Depends(get_db_session)):
    """Temporary implementation - returns empty results"""
    logger.warning(f"Search not implemented yet for PostgreSQL: {item_name} in {city}")
    return []

@router.post("/cheapest-cart-all-chains")
def find_cheapest_cart(cart_request: CartRequest, db: Session = Depends(get_db_session)):
    """Temporary implementation"""
    logger.warning("Cheapest cart calculation not implemented for PostgreSQL yet")
    return {
        "error": "This feature is being migrated to PostgreSQL",
        "city": cart_request.city,
        "items": cart_request.items
    }

# ============= Health Check =============

@router.get("/health")
def health_check(db: Session = Depends(get_db_session)):
    """Check if the price service is healthy"""
    try:
        # Test database connection
        db.execute("SELECT 1")

        # Count records
        store_count = db.query(Store).count()
        price_count = db.query(Price).count()

        return {
            "status": "healthy",
            "database": "connected",
            "stores": store_count,
            "prices": price_count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
