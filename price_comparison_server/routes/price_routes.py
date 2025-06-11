"""
Price Routes Module - Complete Rewrite
Handles all price-related API endpoints with support for cross-chain products
"""

from fastapi import APIRouter, HTTPException, Query
import sqlite3
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
from models.data_models import Price, CartRequest, CartItem
from utils.db_utils import get_db_connection, DBS, get_corrected_city_path

# Import search function for advanced product matching
from services.search_service import search_products_by_name_and_city

# Create router
router = APIRouter(tags=["prices"])

# ============= Helper Classes =============

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

@router.get("/prices/{db_name}/store/{snif_key}", response_model=List[Price])
def get_prices_by_store(db_name: str, snif_key: str):
    """Get all prices for a specific store"""
    if db_name not in DBS:
        raise HTTPException(status_code=400, detail="Invalid database name. Use 'shufersal' or 'victory'.")
    
    # Find the city for this store
    city = None
    for city_dir in os.listdir(DBS[db_name]):
        if os.path.exists(os.path.join(DBS[db_name], city_dir, f"{snif_key}.db")):
            city = city_dir
            break
    
    if not city:
        raise HTTPException(status_code=404, detail=f"Store {snif_key} not found in {db_name}")
    
    try:
        conn = get_db_connection(db_name, city, snif_key)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prices ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching prices for store {snif_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/prices/{db_name}/item_code/{item_code}", response_model=List[Price])
def get_prices_by_item_code(db_name: str, item_code: str):
    """Get all prices for a specific item code across all stores"""
    if db_name not in DBS:
        raise HTTPException(status_code=400, detail="Invalid database name. Use 'shufersal' or 'victory'.")
    
    prices = []
    
    try:
        for city in os.listdir(DBS[db_name]):
            city_path = os.path.join(DBS[db_name], city)
            if os.path.isdir(city_path):
                for db_file in os.listdir(city_path):
                    if db_file.endswith(".db"):
                        snif_key = db_file.replace(".db", "")
                        conn = get_db_connection(db_name, city, snif_key)
                        cursor = conn.cursor()
                        cursor.execute("SELECT * FROM prices WHERE item_code = ?", (item_code,))
                        rows = cursor.fetchall()
                        conn.close()
                        prices.extend([dict(row) for row in rows])
    except Exception as e:
        logger.error(f"Error searching for item code {item_code}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    if not prices:
        raise HTTPException(status_code=404, detail=f"Item code {item_code} not found")
    
    return prices

# ============= City Endpoints =============

@router.get("/cities-list")
def get_cities_list():
    """Get simple list of all cities"""
    cities = set()
    
    for chain_name, chain_path in DBS.items():
        if os.path.exists(chain_path):
            for city in os.listdir(chain_path):
                city_path = os.path.join(chain_path, city)
                if os.path.isdir(city_path):
                    cities.add(city)
    
    return sorted(list(cities))

@router.get("/cities-list-with-stores")
def get_cities_list_with_stores():
    """Get cities with store count information"""
    cities_data = {}
    
    for chain_name, chain_path in DBS.items():
        if os.path.exists(chain_path):
            for city in os.listdir(chain_path):
                city_path = os.path.join(chain_path, city)
                if os.path.isdir(city_path):
                    if city not in cities_data:
                        cities_data[city] = {'shufersal': 0, 'victory': 0}
                    
                    store_count = len([f for f in os.listdir(city_path) if f.endswith('.db')])
                    cities_data[city][chain_name] = store_count
    
    # Format the response
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
def search_products(
    city: str,
    item_name: str,
    group_by_code: bool = Query(True, description="Group identical products by item code"),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=100)
):
    """
    Search for products by name in a specific city.
    Returns cross-chain grouped products when group_by_code=True.
    """
    logger.info(f"Search request: '{item_name}' in {city} (group_by_code={group_by_code})")
    
    try:
        # Use the search service
        results = search_products_by_name_and_city(city, item_name, group_by_code)
        
        if not results:
            logger.info(f"No results found for '{item_name}' in {city}")
            return []
        
        # Apply limit
        limited_results = results[:limit]
        
        logger.info(f"Returning {len(limited_results)} results (from {len(results)} total)")
        return limited_results
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.get("/prices/identical-products/{city}/{item_name}")
def get_identical_products(
    city: str,
    item_name: str,
    limit: int = Query(50, description="Maximum number of results", ge=1, le=100)
):
    """
    Get only products that exist in multiple chains (cross-chain products).
    Useful for direct price comparison of identical items.
    """
    logger.info(f"Searching for identical products: '{item_name}' in {city}")
    
    try:
        # Search with grouping enabled
        all_results = search_products_by_name_and_city(city, item_name, group_by_code=True)
        
        # Filter to only cross-chain products
        cross_chain_products = [
            product for product in all_results 
            if product.get('cross_chain', False)
        ]
        
        if not cross_chain_products:
            logger.info(f"No identical products found across chains for '{item_name}'")
            return []
        
        # Sort by savings (biggest savings first)
        cross_chain_products.sort(
            key=lambda p: p.get('price_comparison', {}).get('savings', 0),
            reverse=True
        )
        
        # Apply limit
        limited_results = cross_chain_products[:limit]
        
        logger.info(f"Found {len(limited_results)} identical products across chains")
        return limited_results
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

# ============= Cart Endpoints =============

@router.post("/cheapest-cart-all-chains")
def find_cheapest_cart(cart_request: CartRequest):
    """
    Find the cheapest store for a shopping cart.
    Handles both single-chain and cross-chain products.
    """
    logger.info(f"Finding cheapest cart in {cart_request.city} for {len(cart_request.items)} items")
    
    # Validate input
    if not cart_request.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Track store inventories
    store_inventories: Dict[str, StoreInventory] = {}
    
    # Search for each item
    for cart_item in cart_request.items:
        logger.info(f"Searching for: {cart_item.item_name} (qty: {cart_item.quantity})")
        
        try:
            # Search with grouping to get best prices
            search_results = search_products_by_name_and_city(
                cart_request.city, 
                cart_item.item_name, 
                group_by_code=True
            )
            
            if not search_results:
                logger.warning(f"No results found for: {cart_item.item_name}")
                continue
            
            # Process all search results
            for result in search_results:
                # Extract price entries from the result
                price_entries = extract_price_entries(result)
                
                # Update store inventories with best prices
                for entry in price_entries:
                    store_key = f"{entry.chain}:{entry.store_id}"
                    
                    # Create store inventory if needed
                    if store_key not in store_inventories:
                        store_inventories[store_key] = StoreInventory(
                            chain=entry.chain,
                            store_id=entry.store_id,
                            items={}
                        )
                    
                    # Update with best price for this item
                    inventory = store_inventories[store_key]
                    if (cart_item.item_name not in inventory.items or 
                        entry.price < inventory.items[cart_item.item_name]):
                        inventory.items[cart_item.item_name] = entry.price
                        logger.debug(f"Updated {store_key}: {cart_item.item_name} = ₪{entry.price}")
                        
        except Exception as e:
            logger.error(f"Error searching for {cart_item.item_name}: {str(e)}")
            continue
    
    # Find stores with all items and calculate totals
    complete_stores = []
    required_items = [item.item_name for item in cart_request.items]
    
    for store_key, inventory in store_inventories.items():
        if inventory.has_all_items(required_items):
            total = inventory.calculate_total(cart_request.items)
            complete_stores.append({
                "chain": inventory.chain,
                "store_id": inventory.store_id,
                "total_price": round(total, 2),
                "item_prices": inventory.items.copy()
            })
            logger.info(f"Complete store: {store_key} = ₪{total:.2f}")
    
    if not complete_stores:
        # Log what we found for debugging
        logger.warning("No stores have all requested items")
        for store_key, inventory in store_inventories.items():
            missing = set(required_items) - set(inventory.items.keys())
            if missing:
                logger.info(f"{store_key} missing: {missing}")
        
        raise HTTPException(
            status_code=404,
            detail="Could not find all items in any single store"
        )
    
    # Sort by total price
    complete_stores.sort(key=lambda s: s['total_price'])
    
    # Get best and worst for savings calculation
    best_store = complete_stores[0]
    worst_store = complete_stores[-1]
    
    # Calculate savings
    savings = worst_store['total_price'] - best_store['total_price']
    savings_percent = (savings / worst_store['total_price'] * 100) if worst_store['total_price'] > 0 else 0
    
    logger.info(f"Best: {best_store['chain']}/{best_store['store_id']} = ₪{best_store['total_price']}")
    logger.info(f"Savings: ₪{savings:.2f} ({savings_percent:.1f}%)")
    
    # Return detailed response
    return {
        "chain": best_store['chain'],
        "store_id": best_store['store_id'],
        "total_price": best_store['total_price'],
        "worst_price": worst_store['total_price'],
        "savings": round(savings, 2),
        "savings_percent": round(savings_percent, 2),
        "city": cart_request.city,
        "items": cart_request.items,
        "item_prices": best_store['item_prices'],
        "all_stores": complete_stores[:10]  # Top 10 stores
    }

# ============= Health Check =============

@router.get("/health")
def health_check():
    """Check if the price service is healthy"""
    try:
        # Check if we can access the databases
        chains_available = {}
        for chain_name, chain_path in DBS.items():
            chains_available[chain_name] = os.path.exists(chain_path)
        
        return {
            "status": "healthy",
            "chains_available": chains_available
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }