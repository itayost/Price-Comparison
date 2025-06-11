from fastapi import APIRouter, HTTPException
import sqlite3
import os
import sys
from typing import List

# Add project root to path for imports if needed
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import models and utilities
from models.data_models import Price, CartRequest, CartItem
from utils.db_utils import get_db_connection, DBS, get_corrected_city_path

# Import old search function for fallback
from services.search_service import search_products_by_name_and_city

# Try to import new search engine
try:
    from search_engine import search_products as new_search_products
    USE_NEW_SEARCH = True
    print("DEBUG: Successfully imported new search engine")
except ImportError as e:
    USE_NEW_SEARCH = False
    print(f"DEBUG: Failed to import search engine: {e}")

router = APIRouter(tags=["prices"])

@router.get("/prices/{db_name}/store/{snif_key}", response_model=List[Price])
def get_prices_by_store(db_name: str, snif_key: str):
    if db_name not in DBS:
        raise HTTPException(status_code=400, detail="Invalid database name. Use 'shufersal' or 'victory'.")
    
    city = None
    for city_dir in os.listdir(DBS[db_name]):
        if os.path.exists(os.path.join(DBS[db_name], city_dir, f"{snif_key}.db")):
            city = city_dir
            break
    
    if not city:
        raise HTTPException(status_code=404, detail="Store not found")
    
    conn = get_db_connection(db_name, city, snif_key)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prices ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

@router.get("/prices/{db_name}/item_code/{item_code}", response_model=List[Price])
def get_prices_by_item_code(db_name: str, item_code: str):
    if db_name not in DBS:
        raise HTTPException(status_code=400, detail="Invalid database name. Use 'shufersal' or 'victory'.")
    
    prices = []
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
    
    if not prices:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return prices

@router.get("/prices/{db_name}/item_name/{item_name}", response_model=List[Price])
def get_prices_by_item_name(db_name: str, item_name: str):
    if db_name not in DBS:
        raise HTTPException(status_code=400, detail="Invalid database name. Use 'shufersal' or 'victory'.")
    
    prices = []
    for city in os.listdir(DBS[db_name]):
        city_path = os.path.join(DBS[db_name], city)
        if os.path.isdir(city_path):
            for db_file in os.listdir(city_path):
                if db_file.endswith(".db"):
                    snif_key = db_file.replace(".db", "")
                    conn = get_db_connection(db_name, city, snif_key)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM prices WHERE item_name LIKE ?", ('%' + item_name + '%',))
                    rows = cursor.fetchall()
                    conn.close()
                    prices.extend([dict(row) for row in rows])
    
    return prices

@router.get("/cities-list-with-stores")
def get_cities_list_extended():
    cities_data = {}
    
    for db_name in DBS:
        db_path = DBS[db_name]
        for city in os.listdir(db_path):
            city_path = os.path.join(db_path, city)
            if os.path.isdir(city_path):
                if city not in cities_data:
                    cities_data[city] = {'shufersal': 0, 'victory': 0}
                
                store_count = len([f for f in os.listdir(city_path) if f.endswith('.db')])
                cities_data[city][db_name] = store_count
    
    formatted_cities = []
    for city, counts in cities_data.items():
        store_info = []
        if counts['shufersal'] > 0:
            store_info.append(f"{counts['shufersal']} shufersal")
        if counts['victory'] > 0:
            store_info.append(f"{counts['victory']} victory")
        formatted_cities.append(f"{city}: {', '.join(store_info)}")
    
    return formatted_cities

@router.get("/cities-list")
def get_cities_list():
    formatted_cities = []
    
    for db_name in DBS:
        db_path = DBS[db_name]
        for city in os.listdir(db_path):
            formatted_cities.append(f"{city}")
    return formatted_cities

@router.post("/cheapest-cart-all-chains")
def get_cheapest_cart_all_chains(cart_request: CartRequest):
    best_price = float('inf')
    best_store = None
    best_chain = None
    
    for db_name in DBS.keys():
        db_path = DBS[db_name]
        city_path = os.path.join(db_path, cart_request.city)
        
        if not os.path.exists(city_path):
            continue
            
        for db_file in os.listdir(city_path):
            if db_file.endswith(".db"):
                snif_key = db_file.replace(".db", "")
                total_price = 0
                items_found = True
                
                try:
                    conn = get_db_connection(db_name, cart_request.city, snif_key)
                    cursor = conn.cursor()
                    
                    for item in cart_request.items:
                        cursor.execute(""" 
                            SELECT item_price 
                            FROM prices 
                            WHERE item_name LIKE ? 
                            ORDER BY timestamp DESC 
                            LIMIT 1
                        """, ('%' + item.item_name + '%',))
                        result = cursor.fetchone()
                        
                        if result:
                            total_price += result['item_price'] * item.quantity
                        else:
                            items_found = False
                            break
                            
                    conn.close()
                    
                    if items_found and total_price < best_price:
                        best_price = total_price
                        best_store = snif_key
                        best_chain = db_name
                        
                except Exception as e:
                    continue
    
    if best_store is None:
        raise HTTPException(status_code=404, detail="Could not find all items in any single store")
    
    return {
        "chain": best_chain,
        "store_id": best_store,
        "total_price": best_price,
        "city": cart_request.city,
        "items": cart_request.items
    }

@router.get("/prices/by-item/{city}/{item_name}")
def get_prices_by_item_and_city(city: str, item_name: str):
    """Get prices for an item in a specific city across all chains."""
    print(f"DEBUG: Search request for '{item_name}' in {city}, using new search: {USE_NEW_SEARCH}")
    
    # Add debugging for incoming request 
    print(f"DEBUG: RECEIVED REQUEST - city: {city}, item_name: {item_name}")
    
    # Use a direct query and ensure results from both chains
    print(f"DEBUG: Starting search for '{item_name}' in {city} with balanced chain results")
    
    # Always use old search to get more comprehensive results
    all_results = search_products_by_name_and_city(city, item_name)
    print(f"DEBUG: Got {len(all_results)} total results")
    
    # Analyze chain distribution in the results
    result_chains = {}
    for item in all_results:
        for price in item.get('prices', []):
            chain = price.get('chain')
            if chain:
                result_chains[chain] = result_chains.get(chain, 0) + 1
                
    print(f"DEBUG: Chain distribution: {result_chains}")
    
    # Check if we have results from both chains
    has_shufersal = 'shufersal' in result_chains and result_chains['shufersal'] > 0
    has_victory = 'victory' in result_chains and result_chains['victory'] > 0
    
    # Balance results between chains
    # Group products by chain
    chain_products = {'shufersal': [], 'victory': [], 'both': []}
    
    for item in all_results:
        # Determine which chains this product appears in
        item_chains = set()
        for price in item.get('prices', []):
            chain = price.get('chain')
            if chain:
                item_chains.add(chain)
        
        # Categorize the item
        if 'shufersal' in item_chains and 'victory' in item_chains:
            chain_products['both'].append(item)
        elif 'shufersal' in item_chains:
            chain_products['shufersal'].append(item)
        elif 'victory' in item_chains:
            chain_products['victory'].append(item)
    
    # Create a balanced set of results
    balanced_results = []
    
    # Add products available in both chains first (they're most valuable)
    both_limit = min(25, len(chain_products['both']))
    balanced_results.extend(chain_products['both'][:both_limit])
    
    # Determine how many results to take from each chain
    # We want to ensure equal representation from both chains
    remaining_slots = 100 - len(balanced_results)
    per_chain = remaining_slots // 2 if remaining_slots > 0 else 0
    
    # If we have both chains, use balanced approach
    if has_shufersal and has_victory:
        print("DEBUG: Both chains present, balancing results")
        # Add equal numbers from each chain
        balanced_results.extend(chain_products['shufersal'][:per_chain])
        balanced_results.extend(chain_products['victory'][:per_chain])
        
        # Fill any remaining slots by alternating between chains
        remaining = 100 - len(balanced_results)
        if remaining > 0:
            # Create a combined list of remaining products from both chains
            remaining_products = []
            chain_idx = {'shufersal': per_chain, 'victory': per_chain}
            
            # Build an alternating list
            for i in range(remaining):
                # Choose which chain to take from next (alternate)
                current_chain = 'shufersal' if i % 2 == 0 else 'victory'
                alt_chain = 'victory' if current_chain == 'shufersal' else 'shufersal'
                
                # Get product from current chain if available, otherwise from alternate
                if chain_idx[current_chain] < len(chain_products[current_chain]):
                    remaining_products.append(chain_products[current_chain][chain_idx[current_chain]])
                    chain_idx[current_chain] += 1
                elif chain_idx[alt_chain] < len(chain_products[alt_chain]):
                    remaining_products.append(chain_products[alt_chain][chain_idx[alt_chain]])
                    chain_idx[alt_chain] += 1
                else:
                    # No more products in either chain
                    break
            
            balanced_results.extend(remaining_products)
    else:
        # We're missing a chain, try to add it
        missing_chain = 'victory' if not has_victory else 'shufersal'
        print(f"DEBUG: Missing chain: {missing_chain}, attempting to add results")
        
        # Try to ensure we get some results from the missing chain
        # For milk specifically, try direct pattern matching
        if item_name == "חלב" or "חלב" in item_name:
            print(f"DEBUG: Special case for milk - trying to add {missing_chain} results")
            # Add whatever we have from the missing chain
            balanced_results.extend(chain_products[missing_chain])
            
            # Then fill remaining slots with products from the chain we do have
            present_chain = 'shufersal' if missing_chain == 'victory' else 'victory'
            
            # Calculate how many more products we need
            remaining = 100 - len(balanced_results)
            if remaining > 0:
                # Add remaining products from the present chain
                balanced_results.extend(chain_products[present_chain][:remaining])
        else:
            # For other products, just add what we have
            # First add from missing chain (if any)
            balanced_results.extend(chain_products[missing_chain])
            
            # Then add from present chain up to the limit
            present_chain = 'shufersal' if missing_chain == 'victory' else 'victory'
            remaining = 100 - len(balanced_results)
            if remaining > 0:
                balanced_results.extend(chain_products[present_chain][:remaining])
    
    print(f"DEBUG: Returning {len(balanced_results)} balanced results")
    
    # Count chain distribution in balanced results
    balanced_chains = {}
    for item in balanced_results:
        for price in item.get('prices', []):
            chain = price.get('chain')
            if chain:
                balanced_chains[chain] = balanced_chains.get(chain, 0) + 1
    
    print(f"DEBUG: Final chain distribution: {balanced_chains}")
    
    # Return balanced results, limited to 100 if needed
    return balanced_results[:100]

# Advanced search endpoint with query parameters
@router.get("/search/{city}")
def advanced_search(city: str, query: str, category: str = None, min_price: float = None, 
                   max_price: float = None, chain: str = None):
    """
    Advanced search with filtering capabilities.
    
    Args:
        city: City to search in
        query: Search query text
        category: Filter by category
        min_price: Minimum price filter
        max_price: Maximum price filter
        chain: Filter by chain
    """
    # Always use new search for advanced search
    if not USE_NEW_SEARCH:
        raise HTTPException(status_code=400, detail="Advanced search requires the new search engine")
    
    # Get base results
    results = new_search_products(query, city)
    
    # Apply filters
    filtered_results = results
    
    # Filter by chain if specified
    if chain:
        filtered_results = [r for r in filtered_results if r['chain'] == chain]
    
    # Filter by price range
    if min_price is not None:
        filtered_results = [r for r in filtered_results if r['price'] >= min_price]
    if max_price is not None:
        filtered_results = [r for r in filtered_results if r['price'] <= max_price]
    
    # Filter by category if implemented in future
    # This would require category tags to be added to products
    
    return filtered_results