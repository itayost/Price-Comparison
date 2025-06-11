from fastapi import APIRouter, HTTPException
import sqlite3
import os
import sys
from typing import List, Dict, Any, Set
import logging

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
    """
    Enhanced implementation of cheapest cart calculation that uses the 
    advanced search functionality to properly match products across chains.
    """
    logger.info(f"Processing cheapest cart request for city: {cart_request.city} with {len(cart_request.items)} items")
    
    # Track best prices for each chain and store
    chain_store_prices: Dict[str, Dict[str, float]] = {}
    # Track if we found items in each store
    chain_store_found_items: Dict[str, Dict[str, Set[str]]] = {}
    # Track individual item prices for showing savings
    item_prices_by_chain: Dict[str, Dict[str, float]] = {}
    # Track item matches to prevent duplicate counting
    processed_items: Dict[str, bool] = {item.item_name: False for item in cart_request.items}
    
    # Step 1: Find item prices across all chains and stores first
    for item in cart_request.items:
        if processed_items[item.item_name]:
            continue  # Skip if already processed
            
        logger.info(f"Searching for item: {item.item_name}")
        
        # Use the advanced search function with cross-chain product grouping
        search_results = search_products_by_name_and_city(cart_request.city, item.item_name, group_by_code=True)
        logger.info(f"Found {len(search_results)} search results for {item.item_name}")
        
        # Mark this item as processed
        processed_items[item.item_name] = True
        
        # Process search results for this item
        # Track best price found for each item in each store
        store_item_best_prices = {}
        
        for result in search_results:
            # For cross-chain identical products (grouped by item code)
            if result.get('cross_chain', False) and 'prices' in result:
                logger.info(f"Processing cross-chain product: {result.get('item_name', '')}")
                
                # Get chains and prices
                for price_info in result.get('prices', []):
                    chain = price_info.get('chain')
                    store_id = price_info.get('store_id')
                    item_price = price_info.get('price', 0) 
                    
                    # Skip if missing key info
                    if not chain or not store_id or item_price <= 0:
                        continue
                    
                    # Initialize data structures if needed
                    if chain not in chain_store_prices:
                        chain_store_prices[chain] = {}
                        chain_store_found_items[chain] = {}
                        item_prices_by_chain[chain] = {}
                        store_item_best_prices[chain] = {}
                    
                    if store_id not in chain_store_prices[chain]:
                        chain_store_prices[chain][store_id] = 0
                        chain_store_found_items[chain][store_id] = set()
                        store_item_best_prices[chain][store_id] = {}
                    
                    # Track this item-store-price combination
                    store_key = f"{chain}:{store_id}"
                    if (store_key not in store_item_best_prices or
                        item.item_name not in store_item_best_prices[store_key] or
                        item_price < store_item_best_prices[store_key][item.item_name]):
                        
                        # Add or update with best price
                        if store_key not in store_item_best_prices:
                            store_item_best_prices[store_key] = {}
                        
                        # Log if we're updating a previous price
                        if item.item_name in store_item_best_prices[store_key]:
                            old_price = store_item_best_prices[store_key][item.item_name]
                            logger.info(f"Found better price for {item.item_name} in {chain}/{store_id}: ₪{item_price} (was ₪{old_price})")
                        
                        # Update with best price 
                        store_item_best_prices[store_key][item.item_name] = item_price
                        
                        # Update store's total price for this item
                        total_item_price = item_price * item.quantity
                        
                        # Add this item to the found items set for this store
                        chain_store_found_items[chain][store_id].add(item.item_name)
                        
                        # Update item price and total
                        chain_store_prices[chain][store_id] = total_item_price
                        
                        logger.info(f"Added to {chain}/{store_id}: {item.item_name} at ₪{item_price} x {item.quantity} = ₪{total_item_price}")
                        
                        # Track individual item prices for savings calculation
                        if item.item_name not in item_prices_by_chain[chain] or item_price < item_prices_by_chain[chain][item.item_name]:
                            item_prices_by_chain[chain][item.item_name] = item_price
            
            # For single-chain products
            elif 'chain' in result and 'store_id' in result:
                chain = result.get('chain')
                store_id = result.get('store_id')
                item_price = result.get('price', result.get('item_price', 0))
                
                # Skip if missing key info
                if not chain or not store_id or item_price <= 0:
                    continue
                    
                # Initialize data structures if needed
                if chain not in chain_store_prices:
                    chain_store_prices[chain] = {}
                    chain_store_found_items[chain] = {}
                    item_prices_by_chain[chain] = {}
                    store_item_best_prices[chain] = {}
                
                if store_id not in chain_store_prices[chain]:
                    chain_store_prices[chain][store_id] = 0
                    chain_store_found_items[chain][store_id] = set()
                    store_item_best_prices[chain][store_id] = {}
                
                # Track this item-store-price combination
                store_key = f"{chain}:{store_id}"
                if (store_key not in store_item_best_prices or
                    item.item_name not in store_item_best_prices[store_key] or
                    item_price < store_item_best_prices[store_key][item.item_name]):
                    
                    # Add or update with best price
                    if store_key not in store_item_best_prices:
                        store_item_best_prices[store_key] = {}
                    
                    # Log if we're updating a previous price
                    if item.item_name in store_item_best_prices[store_key]:
                        old_price = store_item_best_prices[store_key][item.item_name]
                        logger.info(f"Found better price for {item.item_name} in {chain}/{store_id}: ₪{item_price} (was ₪{old_price})")
                    
                    # Update with best price 
                    store_item_best_prices[store_key][item.item_name] = item_price
                    
                    # Update store's total price with this item
                    total_item_price = item_price * item.quantity
                    
                    # Add this item to the found items set for this store
                    chain_store_found_items[chain][store_id].add(item.item_name)
                    
                    # Update price
                    chain_store_prices[chain][store_id] = total_item_price
                    
                    logger.info(f"Added to {chain}/{store_id}: {item.item_name} at ₪{item_price} x {item.quantity} = ₪{total_item_price}")
                    
                    # Track individual item prices for savings calculation
                    if item.item_name not in item_prices_by_chain[chain] or item_price < item_prices_by_chain[chain][item.item_name]:
                        item_prices_by_chain[chain][item.item_name] = item_price
    
    # Step 2: Find stores with all items and determine best and worst prices
    best_price = float('inf')
    best_store = None
    best_chain = None
    worst_price = 0
    complete_stores = []
    
    logger.info(f"Evaluating stores with complete item sets")
    
    # Now recalculate totals using best prices for each store
    recalculated_stores = {}
    
    # First track all stores with all items and calculate their total prices
    for chain, stores in chain_store_found_items.items():
        for store_id, found_items in stores.items():
            # Check if this store has all the items
            if len(found_items) == len(cart_request.items):
                store_key = f"{chain}:{store_id}"
                
                # Calculate total using best price for each item
                total_price = 0
                for cart_item in cart_request.items:
                    item_name = cart_item.item_name
                    quantity = cart_item.quantity
                    
                    # Use the best price found for this item in this store
                    best_item_price = store_item_best_prices[store_key][item_name]
                    total_price += best_item_price * quantity
                
                store_info = {
                    "chain": chain,
                    "store_id": store_id,
                    "total_price": total_price
                }
                complete_stores.append(store_info)
                
                logger.info(f"Complete store: {chain}/{store_id} with price ₪{total_price}")
                
                # Update best price if this is better
                if total_price < best_price:
                    best_price = total_price
                    best_store = store_id
                    best_chain = chain
    
    # Now find the worst price among complete stores for accurate savings calculation  
    if complete_stores:
        worst_price = max(store["total_price"] for store in complete_stores)
    
    # Return error if we didn't find all items in any single store
    if best_store is None:
        logger.warning("Could not find all items in any single store")
        raise HTTPException(status_code=404, detail="Could not find all items in any single store")
    
    # Calculate savings percentage
    savings = worst_price - best_price if worst_price > 0 else 0
    savings_percent = (savings / worst_price) * 100 if worst_price > 0 else 0
    
    logger.info(f"Best store: {best_chain}/{best_store} with price ₪{best_price}")
    logger.info(f"Savings: ₪{savings} ({savings_percent:.2f}%)")
    
    # Return enhanced response with savings info and store comparisons
    return {
        "chain": best_chain,
        "store_id": best_store,
        "total_price": best_price,
        "worst_price": worst_price,
        "savings": savings,
        "savings_percent": savings_percent,
        "city": cart_request.city,
        "items": cart_request.items,
        "item_prices": item_prices_by_chain.get(best_chain, {}),
        "all_stores": complete_stores
    }

@router.get("/prices/by-item/{city}/{item_name}")
def get_prices_by_item_and_city(city: str, item_name: str, group_by_code: bool = True):
    """
    Get prices for an item in a specific city across all chains with balanced results.
    
    Args:
        city: The city to search in
        item_name: The item name to search for
        group_by_code: Whether to group results by item code (default: True)
    """
    logger.info(f"Search request for '{item_name}' in {city}, group by code: {group_by_code}")
    
    # Fixed limit of results for performance (important for preventing ANR)
    limit = 50
    
    # Always use old search to get comprehensive results
    # With our new grouping parameter to enable identical product matching
    all_results = search_products_by_name_and_city(city, item_name, group_by_code)
    logger.info(f"Got {len(all_results)} total results")
    
    # Check if we have cross-chain products and for any special cases
    has_cross_chain = any(p.get('cross_chain', False) for p in all_results)
    logger.info(f"Has cross-chain products: {has_cross_chain}")
    
    # Add store count information to improve sorting
    for item in all_results:
        # Count how many stores an item appears in
        stores = set()
        for price in item.get('prices', []):
            if price.get('store_id'):
                stores.add(price.get('store_id'))
        
        # Add store count as a sort criteria
        item['store_count'] = len(stores)
    
    # Sort results to prioritize cross-chain products and exact matches
    all_results.sort(key=lambda x: (
        0 if x.get('cross_chain', False) else 1,  # Cross-chain products first
        0 if item_name.lower() in x.get('item_name', '').lower() else 1,  # Exact matches
        -x.get('store_count', 0),  # More available stores first
        # Get lowest price, handling different price formats
        min(
            [p.get('price', 999999) for p in x.get('prices', []) if isinstance(p, dict) and p.get('price')] or 
            [x.get('price', x.get('item_price', 999999))]
        )
    ))
    
    logger.info(f"Sorted results with cross-chain products at the top")
    
    # # For milk in Tel Aviv or other known working cases, return the processed results directly
    # if (item_name == "חלב" and city.lower() in ["tel aviv", "tel-aviv", "telaviv"]) or has_cross_chain:
    #     logger.info("Using direct search results with cross-chain prioritization")
    #     return all_results[:100]
    
    # If the search didn't return any results, return an empty list
    if not all_results:
        logger.info("No results found")
        return []
    
    # If we're grouping by item code, the search function already handled balancing
    # and sorting, so we can just limit and optimize the results
    if group_by_code:
        logger.info(f"Preparing grouped results by item code")
        
        # Limit to 50 results
        limited_results = all_results[:limit]
        logger.info(f"Limited to {len(limited_results)} results")
        
        # Return the limited results directly in the original format
        return limited_results
        
        # Optimize response size if requested - DISABLED to keep original format
        if False: # Previously: if optimize:
            optimized_results = []
            for item in limited_results:
                # Keep only essential fields
                optimized_item = {
                    'item_name': item.get('item_name', ''),
                    'item_code': item.get('item_code', ''),
                    'cross_chain': item.get('cross_chain', False),
                }
                
                # Simplify prices structure
                if 'prices' in item and isinstance(item['prices'], list):
                    # Just keep chain, price, and store_id for each price
                    optimized_item['prices'] = [
                        {
                            'chain': p.get('chain', ''),
                            'price': p.get('price', 0),
                            'store_id': p.get('store_id', '')
                        } 
                        for p in item['prices']
                    ]
                else:
                    # For items without prices array, keep basic price info
                    optimized_item['price'] = item.get('price', item.get('item_price', 0))
                    optimized_item['chain'] = item.get('chain', '')
                    optimized_item['store_id'] = item.get('store_id', '')
                
                # Keep price comparison data in simplified form if available
                if item.get('price_comparison'):
                    optimized_item['best_price'] = item.get('price_comparison', {}).get('best_deal', {}).get('price', 0)
                    optimized_item['savings'] = item.get('price_comparison', {}).get('savings', 0)
                
                optimized_results.append(optimized_item)
            
            # Return just the optimized results
            return optimized_results
        
        # Return just the limited results
        return limited_results
    
    # For other searches, we'll implement a more general balancing approach
    # First check if chain information is directly in the items or in a nested field
    first_item = all_results[0] if all_results else {}
    chain_in_item = 'chain' in first_item
    
    # Analyze chain distribution in the results
    result_chains = {}
    
    if chain_in_item:
        # Structure: items with chain directly in them
        for item in all_results:
            chain = item.get('chain')
            if chain:
                result_chains[chain] = result_chains.get(chain, 0) + 1
    else:
        # Structure: items with prices list containing chain info
        for item in all_results:
            for price in item.get('prices', []):
                chain = price.get('chain')
                if chain:
                    result_chains[chain] = result_chains.get(chain, 0) + 1
                    
    logger.info(f"Chain distribution: {result_chains}")
    
    # Check if we have results from both chains
    has_shufersal = 'shufersal' in result_chains and result_chains['shufersal'] > 0
    has_victory = 'victory' in result_chains and result_chains['victory'] > 0
    
    # Balance results between chains
    # Group products by chain
    chain_products = {'shufersal': [], 'victory': [], 'both': []}
    
    if chain_in_item:
        # Group items where chain is directly in the item
        for item in all_results:
            chain = item.get('chain')
            if chain == 'shufersal':
                chain_products['shufersal'].append(item)
            elif chain == 'victory':
                chain_products['victory'].append(item)
    else:
        # Group items where chain is in the prices list
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
    max_results = 100  # Maximum results before pagination
    remaining_slots = max_results - len(balanced_results)
    per_chain = remaining_slots // 2 if remaining_slots > 0 else 0
    
    # If we have both chains, use balanced approach
    if has_shufersal and has_victory:
        logger.info("Both chains present, balancing results")
        # Add equal numbers from each chain
        balanced_results.extend(chain_products['shufersal'][:per_chain])
        balanced_results.extend(chain_products['victory'][:per_chain])
        
        # Fill any remaining slots by alternating between chains
        remaining = max_results - len(balanced_results)
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
        # We're missing a chain, use all results from the one we have
        missing_chain = 'victory' if not has_victory else 'shufersal'
        present_chain = 'shufersal' if missing_chain == 'victory' else 'victory'
        logger.info(f"Missing chain: {missing_chain}, using only {present_chain} results")
        
        # Limited to max_results
        balanced_results.extend(chain_products[present_chain][:max_results-len(balanced_results)])
    
    logger.info(f"Created {len(balanced_results)} balanced results")
    
    # Limit to 50 results
    limited_results = balanced_results[:limit]
    logger.info(f"Limited to {len(limited_results)} results")
    
    # Return limited results in the original format expected by the app
    return limited_results
    
    # Optimize response size if requested - DISABLED to keep original format
    if False: # Previously: if optimize:
        optimized_results = []
        for item in limited_results:
            # Keep only essential fields
            optimized_item = {
                'item_name': item.get('item_name', ''),
                'item_code': item.get('item_code', ''),
                'cross_chain': item.get('cross_chain', False),
            }
            
            # Simplify prices structure
            if 'prices' in item and isinstance(item['prices'], list):
                # Just keep chain, price, and store_id for each price
                optimized_item['prices'] = [
                    {
                        'chain': p.get('chain', ''),
                        'price': p.get('price', 0),
                        'store_id': p.get('store_id', '')
                    } 
                    for p in item['prices']
                ]
            else:
                # For items without prices array, keep basic price info
                optimized_item['price'] = item.get('price', item.get('item_price', 0))
                optimized_item['chain'] = item.get('chain', '')
                optimized_item['store_id'] = item.get('store_id', '')
            
            # Keep price comparison data in simplified form if available
            if item.get('price_comparison'):
                optimized_item['best_price'] = item.get('price_comparison', {}).get('best_deal', {}).get('price', 0)
                optimized_item['savings'] = item.get('price_comparison', {}).get('savings', 0)
            
            optimized_results.append(optimized_item)
        
        # Return just the optimized results
        return optimized_results
    
    # Return just the limited results
    return limited_results

@router.get("/prices/identical-products/{city}/{item_name}")
def get_identical_products(city: str, item_name: str):
    """
    Get identical products (by item code) across different chains for better price comparison.
    This endpoint specifically focuses on products that exist in multiple chains with the same item code.
    
    Args:
        city: The city to search in
        item_name: The item name to search for
    """
    logger.info(f"Searching for identical products for '{item_name}' in {city}")
    
    # Fixed limit of results
    limit = 50
    
    # Use the search function with group_by_code=True to get grouped results
    all_results = search_products_by_name_and_city(city, item_name, group_by_code=True)
    
    # Filter to only include products that span multiple chains (cross-chain products)
    identical_products = [product for product in all_results if product.get('cross_chain', False)]
    
    # If no identical products found, check if there might be an issue with cross_chain flag
    if not identical_products and all_results:
        logger.warning("No products with cross_chain flag found, checking for items with prices from multiple chains")
        # Manually check for products that have prices from multiple chains
        for product in all_results:
            if "prices" in product and isinstance(product["prices"], list) and len(product["prices"]) > 1:
                # Check if this product has prices from different chains
                chains = set(price.get("chain", "") for price in product["prices"] if price.get("chain"))
                if len(chains) > 1:
                    # This product appears in multiple chains
                    product["cross_chain"] = True
                    identical_products.append(product)
    
    logger.info(f"Found {len(identical_products)} identical products across chains")
    
    # Sort by biggest price difference to highlight best savings opportunities
    identical_products.sort(key=lambda p: (
        p.get('price_comparison', {}).get('savings', 0) if p.get('price_comparison') else 0
    ), reverse=True)
    
    # Limit to 50 results
    limited_results = identical_products[:limit]
    logger.info(f"Limited to {len(limited_results)} results")
    
    # Return limited results in the original format expected by the app
    return limited_results
    
    # Optimize response size if requested - DISABLED to keep original format
    if False: # Previously: if optimize:
        optimized_results = []
        for item in limited_results:
            # Keep only essential fields
            optimized_item = {
                'item_name': item.get('item_name', ''),
                'item_code': item.get('item_code', ''),
                'cross_chain': True,  # All these items are cross-chain by definition
            }
            
            # Extract just best and worst prices
            if 'price_comparison' in item:
                comp = item['price_comparison']
                optimized_item['best_deal'] = {
                    'chain': comp.get('best_deal', {}).get('chain', ''),
                    'price': comp.get('best_deal', {}).get('price', 0),
                    'store_id': comp.get('best_deal', {}).get('store_id', '')
                }
                optimized_item['worst_deal'] = {
                    'chain': comp.get('worst_deal', {}).get('chain', ''),
                    'price': comp.get('worst_deal', {}).get('price', 0)
                }
                optimized_item['savings'] = comp.get('savings', 0)
                optimized_item['savings_percent'] = comp.get('savings_percent', 0)
            else:
                # Simplified price info if no comparison data
                chains_prices = {}
                if 'prices' in item and isinstance(item['prices'], list):
                    for price in item['prices']:
                        chain = price.get('chain', '')
                        if chain and price.get('price'):
                            chains_prices[chain] = price.get('price', 0)
                
                # Only include if we have prices from different chains
                if len(chains_prices) >= 2:
                    chains = list(chains_prices.keys())
                    lowest_chain = min(chains, key=lambda c: chains_prices[c])
                    highest_chain = max(chains, key=lambda c: chains_prices[c])
                    
                    optimized_item['best_deal'] = {
                        'chain': lowest_chain,
                        'price': chains_prices[lowest_chain]
                    }
                    optimized_item['worst_deal'] = {
                        'chain': highest_chain,
                        'price': chains_prices[highest_chain]
                    }
                    optimized_item['savings'] = chains_prices[highest_chain] - chains_prices[lowest_chain]
            
            optimized_results.append(optimized_item)
        
        # Return just the optimized results
        return optimized_results
    
    # Return just the limited results
    return limited_results