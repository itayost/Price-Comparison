"""
Original Search Service Module

This module contains the original search implementation for backward compatibility.
For new implementations, use the search_engine module instead.
"""

import os
import sqlite3
import sys
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

# Add project root to path for imports if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.db_utils import get_db_connection, get_corrected_city_path, DBS
from utils.product_utils import extract_product_weight, get_price_per_unit, generate_cross_chain_comparison

# Original search implementation from api_server.py
def search_products_by_name_and_city(city: str, item_name: str, group_by_code: bool = False) -> List[Dict[str, Any]]:
    """
    Legacy search function from the original api_server.py.
    
    Args:
        city: The city to search in
        item_name: The item name to search for
        group_by_code: Whether to group results by item code (new feature)
    
    Returns:
        List of products matching the search criteria
    """
    print("\n==== NEW SEARCH REQUEST ====")
    print(f"Searching for '{item_name}' in city '{city}'")
    print(f"Group by code: {group_by_code}")
    
    results = []
    search_patterns = []
    
    # Special handling for short search terms
    if len(item_name) <= 3:
        print("\n==== SHORT SEARCH TERM HANDLING ====")
        # For short search terms like 'דוב', add expanded patterns
        if 'דוב' in item_name:
            search_patterns.extend(['%דובונים%', '%דובדבן%', '%דובים%'])
        elif 'במ' in item_name:
            search_patterns.extend(['%במבה%', '%במבה מתוקה%', '%במבה נוגט%'])
        elif 'דג' in item_name:
            search_patterns.extend(['%דגני%', '%דג%'])
        elif 'תה' in item_name:
            search_patterns.extend(['%תה%', '%משקה%', '%שתיה%'])
        elif 'גב' in item_name:
            search_patterns.extend(['%גבינה%', '%גבינת%'])
        elif 'חל' in item_name:
            search_patterns.extend(['%חלב%', '%חלבי%'])
        elif 'קוק' in item_name:
            search_patterns.extend(['%קוקה%', '%קולה%', '%קוקוס%'])
        # Default pattern for very short terms
        search_patterns.append(f'%{item_name}%')
    else:
        # Standard search patterns
        search_patterns = [
            f'{item_name}%',  # Starts with
            f' {item_name} ',  # Exact match
            f' {item_name}%',  # Space before
            f'%{item_name}%'   # Contains
        ]
    
    print("\n==== DIRECT DATABASE CHECKS ====")
    # Check database availability before running search
    for chain, path in [('Victory', 'victory_prices'), ('Shufersal', 'shufersal_prices')]:
        city_path = get_corrected_city_path(path, city)
        city_exists = city_path is not None and os.path.exists(city_path)
        
        if chain == 'Victory' and city_exists:
            # For Victory, directly check specific stores
            stores = os.listdir(city_path)
            for store_file in stores:
                if store_file.endswith('.db'):
                    full_path = os.path.join(city_path, store_file)
                    print(f"Checking Victory at: {full_path}, exists: {os.path.exists(full_path)}")
                    
                    # Emergency fix for Victory - direct query for short terms
                    conn = sqlite3.connect(full_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # Only do direct fetch for Victory since we've had issues with it
                    victory_items = []
                    for pattern in search_patterns:
                        cursor.execute("SELECT * FROM prices WHERE item_name LIKE ? LIMIT 100", (pattern,))
                        for row in cursor.fetchall():
                            item_dict = dict(row)
                            item_dict['chain'] = 'victory'
                            item_dict['store_id'] = store_file.replace('.db', '')
                            
                            # Add to our results list if not already there
                            if not any(r['item_name'] == item_dict['item_name'] and r['chain'] == 'victory' for r in victory_items):
                                victory_items.append(item_dict)
                    
                    print(f"Victory direct count: {len(victory_items)}")
                    # Print a few example items
                    for i, item in enumerate(victory_items[:5]):
                        print(f"Victory item: {item['item_name']}, price: {item['item_price']}")
                        
                    results.extend(victory_items)
                    
                    conn.close()
        
        elif chain == 'Shufersal' and city_exists:
            # For Shufersal, just verify one store to confirm city is valid
            stores = os.listdir(city_path)
            if stores:
                first_store = next((s for s in stores if s.endswith('.db')), None)
                if first_store:
                    full_path = os.path.join(city_path, first_store)
                    print(f"Checking Shufersal at: {city_path}, exists: {os.path.exists(city_path)}")
                    
                    # Get count only for debugging
                    conn = sqlite3.connect(full_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    shufersal_count = 0
                    for pattern in search_patterns:
                        cursor.execute("SELECT COUNT(*) FROM prices WHERE item_name LIKE ? LIMIT 100", (pattern,))
                        count = cursor.fetchone()[0]
                        shufersal_count += count
                    
                    print(f"Shufersal direct count in {first_store}: {shufersal_count}")
                    conn.close()
    
    # Regular search across chains
    chains_to_search = [('shufersal', 'shufersal_prices'), ('victory', 'victory_prices')]
    print(f"DEBUG: Searching in chains: {chains_to_search}")
    
    print("\n==== CHAIN PROCESSING ====")
    for chain, db_path in chains_to_search:
        # Get path for the city, correcting case sensitivity if needed
        city_path = get_corrected_city_path(db_path, city)
        abs_path = os.path.abspath(city_path) if city_path else None
        
        print(f"Chain: {chain}, Path: {city_path}, Absolute: {abs_path}")
        print(f"Path exists check: {city_path is not None and os.path.exists(city_path)}")
        
        # Skip if the city directory doesn't exist for this chain
        if not city_path or not os.path.exists(city_path) or not os.path.isdir(city_path):
            continue
            
        print(f"Is directory check: {os.path.isdir(city_path)}")
        
        # Get store database files
        store_files = [f for f in os.listdir(city_path) if f.endswith('.db')]
        if len(store_files) > 3:
            print(f"Store files for {chain}: {store_files[:3]}... ({len(store_files)} total)")
        else:
            print(f"Store files for {chain}: {store_files}")
        
        if not store_files:
            continue
            
        print(f"Processing chain: {chain} in {city} with path {city_path}")
        print(f"DEBUG: Found {len(store_files)} store files in {chain}/{city}")
        
        for store_file in store_files:
            snif_key = store_file.replace('.db', '')
            print(f"DEBUG: Processing store {snif_key} in {chain}/{city}")
            
            if chain == 'victory':
                print(f"=== VICTORY STORE TESTING: {snif_key} ===")
                conn = get_db_connection(chain, city, snif_key)
                cursor = conn.cursor()
                
                # Special query for debugging Victory data
                direct_query = f"SELECT item_name, item_price FROM prices WHERE item_name LIKE '%{search_patterns[-1][1:-1]}%' LIMIT 5"
                print(f"Running direct query: {direct_query}")
                cursor.execute(direct_query)
                direct_rows = cursor.fetchall()
                print(f"Direct query found {len(direct_rows)} rows")
            
            # Search for items in this store
            for pattern in search_patterns:
                conn = get_db_connection(chain, city, snif_key)
                cursor = conn.cursor()
                
                print(f"Trying pattern '{pattern}' in {chain}/{snif_key}")
                
                try:
                    cursor.execute(f"SELECT * FROM prices WHERE item_name LIKE ? LIMIT 200", (pattern,))
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        item_dict = dict(row)
                        item_dict['chain'] = chain
                        item_dict['store_id'] = snif_key
                        
                        # Calculate price per unit if possible
                        weight_info = extract_product_weight(item_dict.get('item_name', ''))
                        if weight_info[0] and weight_info[1]:
                            item_dict['weight'] = weight_info[0]
                            item_dict['unit'] = weight_info[1]
                            # Calculate price per unit if we have a price and weight
                            if 'item_price' in item_dict:
                                price_per_unit = item_dict['item_price'] / item_dict['weight']
                                item_dict['price_per_unit'] = price_per_unit
                        
                        # Add to our results list if not already there
                        if not any(r['item_name'] == item_dict['item_name'] and r['chain'] == chain and r['store_id'] == snif_key for r in results):
                            # Print first few matches for debugging
                            if len(results) < 50:
                                print(f"Found in {chain}/{snif_key}: '{item_dict['item_name']}' for {item_dict['item_price']}")
                            results.append(item_dict)
                except Exception as e:
                    print(f"Error searching {chain}/{snif_key}: {e}")
                finally:
                    conn.close()
    
    # Check for emergency fix for Victory products if needed
    if 'victory' not in [r['chain'] for r in results] and len(results) > 0:
        print("EMERGENCY FIX: Directly searching Victory database")
        city_path = get_corrected_city_path('victory_prices', city)
        
        if city_path and os.path.exists(city_path) and os.path.isdir(city_path):
            victory_stores = [f for f in os.listdir(city_path) if f.endswith('.db')]
            
            if victory_stores:
                first_store = victory_stores[0]
                victory_path = os.path.join(city_path, first_store)
                print(f"Using Victory database: {victory_path}")
                
                conn = sqlite3.connect(victory_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Try various fallback patterns to find *something*
                for fallback_pattern in [
                    f"%{search_patterns[-1][1:-1]}%",  # Original pattern 
                    f"%{item_name[:2]}%",  # First 2 chars
                    "%סוכ.%" if 'סוכר' in item_name else None,  # Sugar-related
                    "%שוקו%" if 'שוקולד' in item_name else None,  # Chocolate-related
                    "%חלב%" if 'חלב' in item_name else None,  # Milk-related
                    "%במבה%" if 'במב' in item_name else None,  # Common snack
                ]:
                    if fallback_pattern:
                        print(f"Trying Victory search: SELECT * FROM prices WHERE item_name LIKE '{fallback_pattern}' LIMIT 8")
                        cursor.execute("SELECT * FROM prices WHERE item_name LIKE ? LIMIT 8", (fallback_pattern,))
                        rows = cursor.fetchall()
                        
                        if rows:
                            for row in rows:
                                item_dict = dict(row)
                                item_dict['chain'] = 'victory'
                                item_dict['store_id'] = first_store.replace('.db', '')
                                results.append(item_dict)
                            break  # Stop after first successful query
                            
                if not any(r['chain'] == 'victory' for r in results):
                    print("Attempting broader category search for Victory items")
                    # Try to find at least some products from the same general category
                    # This ensures we show at least some products from Victory
                    category_terms = {
                        'dairy': ['חלב', 'גבינה', 'יוגורט'],
                        'snacks': ['במבה', 'ביסלי', 'חטיף'],
                        'drinks': ['משקה', 'שתיה', 'מים'],
                        'sweets': ['שוקולד', 'ממתק', 'חטיף'],
                        'bread': ['לחם', 'פיתה', 'חלה'],
                        'cleaning': ['ניקוי', 'אקונומיקה', 'סבון'],
                        'paper': ['נייר', 'טואלט', 'מגבת'],
                    }
                    
                    # Try to guess the category based on item name
                    guessed_category = None
                    for category, terms in category_terms.items():
                        if any(term in item_name for term in terms):
                            guessed_category = category
                            break
                            
                    if guessed_category:
                        # Try to find some items in this category
                        for term in category_terms.get(guessed_category, []):
                            cursor.execute("SELECT * FROM prices WHERE item_name LIKE ? LIMIT 5", (f'%{term}%',))
                            rows = cursor.fetchall()
                            
                            if rows:
                                for row in rows:
                                    item_dict = dict(row)
                                    item_dict['chain'] = 'victory'
                                    item_dict['store_id'] = first_store.replace('.db', '')
                                    results.append(item_dict)
                                break  # Stop after first successful query
                
                conn.close()
    
    # Group by chain for reporting purposes
    chain_counts = {}
    for r in results:
        chain = r.get('chain', 'unknown')
        chain_counts[chain] = chain_counts.get(chain, 0) + 1
    
    print(f"Grouped by chain - " + ", ".join([f"{k.capitalize()}: {v}" for k, v in chain_counts.items()]))
    
    # Ensure we return price as a numeric value
    for r in results:
        if 'item_price' in r:
            r['price'] = r['item_price']
    
    print(f"Found {len(results)} total results for '{item_name}' in '{city}'")
    
    # Apply item code grouping if requested
    if group_by_code:
        print("\n==== GROUPING PRODUCTS BY ITEM CODE ====")
        grouped_results = group_products_by_item_code(results)
        print(f"Found {len(grouped_results)} grouped results after grouping by item code")
        return grouped_results
    
    # Return the results, balancing between chains
    return balance_results(results)

def balance_results(results: List[Dict[str, Any]], limit: int = 100) -> List[Dict[str, Any]]:
    """
    Balance results between different chains to ensure representation.
    This avoids having results from only one chain.
    """
    # Group by chain
    chain_results = {}
    for item in results:
        chain = item.get('chain', 'unknown')
        if chain not in chain_results:
            chain_results[chain] = []
        chain_results[chain].append(item)
    
    # Balance results if we have multiple chains
    balanced_results = []
    
    chains = list(chain_results.keys())
    if len(chains) > 1:
        # Take alternating items from each chain
        i = 0
        while len(balanced_results) < limit:
            chain = chains[i % len(chains)]
            items = chain_results[chain]
            if items:
                balanced_results.append(items.pop(0))
            else:
                # Remove this chain from the list if it has no more items
                chains.remove(chain)
                if not chains:
                    break
            i += 1
    else:
        # Just return all results from the single chain we have
        balanced_results = results[:limit]
    
    return balanced_results

def group_products_by_item_code(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group products by item code to identify identical products across different chains.
    
    Args:
        products: List of product dictionaries from search results
        
    Returns:
        List of grouped products, with cross-chain products merged
    """
    print(f"Starting grouping with {len(products)} products")
    
    # First, filter out products with no item code or invalid codes
    valid_products = []
    for product in products:
        item_code = product.get('item_code')
        if item_code and str(item_code).strip() not in ('0', ''):
            # Normalize item code
            product['item_code'] = str(item_code).strip()
            valid_products.append(product)
            
    print(f"Found {len(valid_products)} products with valid item codes")
    
    # Group products by item code
    item_code_groups = {}
    for product in valid_products:
        item_code = product['item_code']
        if item_code not in item_code_groups:
            item_code_groups[item_code] = []
        item_code_groups[item_code].append(product)
    
    print(f"Created {len(item_code_groups)} item code groups")
    
    # Create a new list of products with cross-chain items merged
    grouped_products = []
    
    # Track item codes we've processed
    processed_item_codes = set()
    
    cross_chain_count = 0
    single_chain_count = 0
    
    # Process items with the same item code across multiple chains
    for item_code, products_with_code in item_code_groups.items():
        # Skip if already processed
        if item_code in processed_item_codes:
            continue
            
        # Check if this item code appears in multiple chains
        chains = set(p.get('chain', '') for p in products_with_code)
        print(f"Item code {item_code}: Found in {len(chains)} chains with {len(products_with_code)} products")
        
        if len(chains) > 1 and len(products_with_code) > 1:
            # This is a cross-chain identical product - merge it
            cross_chain_count += 1
            print(f"Cross-chain product found with item code {item_code} in chains: {chains}")
            
            # Choose the best product name (prefer Shufersal as they usually have better descriptions)
            shufersal_products = [p for p in products_with_code if p.get('chain') == 'shufersal']
            if shufersal_products:
                base_product = shufersal_products[0].copy()
            else:
                # If no Shufersal product, just use the first one
                base_product = products_with_code[0].copy()
            
            print(f"Base product name: {base_product.get('item_name', 'Unknown')}")
            
            # Create a merged product
            merged_product = {
                'item_name': base_product['item_name'],
                'item_code': item_code,
                'prices': [],
                'cross_chain': True,  # Flag indicating this is a cross-chain product
                'chains': list(chains)
            }
            
            # Add all prices from all chains
            for product in products_with_code:
                price_value = product.get('price', product.get('item_price', 0))
                merged_product['prices'].append({
                    'chain': product.get('chain', 'unknown'),
                    'store_id': product.get('store_id', ''),
                    'price': price_value,
                    'original_name': product.get('item_name', ''),
                    'timestamp': product.get('timestamp', '')
                })
                print(f"Added price from {product.get('chain', 'unknown')}: {price_value}")
            
            # Sort prices by price (lowest first)
            merged_product['prices'].sort(key=lambda p: p.get('price', 999999))
            
            # Add price comparison data
            comparison = generate_cross_chain_comparison(merged_product)
            if comparison:
                merged_product['price_comparison'] = comparison
                print(f"Price comparison: {comparison}")
            
            # Add to results
            grouped_products.append(merged_product)
            
            # Mark as processed
            processed_item_codes.add(item_code)
        else:
            # Single chain product, add them all individually
            single_chain_count += 1
            for product in products_with_code:
                grouped_products.append(product)
            
            # Mark as processed
            processed_item_codes.add(item_code)
    
    print(f"Processed {cross_chain_count} cross-chain product groups and {single_chain_count} single-chain product groups")
    
    # Add remaining products that don't have valid item codes
    remaining_count = 0
    for product in products:
        item_code = product.get('item_code')
        # If product doesn't have a valid item code or it hasn't been processed yet, add it
        if not item_code or str(item_code).strip() in ('0', '') or str(item_code).strip() not in processed_item_codes:
            grouped_products.append(product)
            remaining_count += 1
            if item_code and str(item_code).strip() not in ('0', ''):
                processed_item_codes.add(str(item_code).strip())
    
    print(f"Added {remaining_count} remaining products without valid item codes")
    print(f"Total grouped products: {len(grouped_products)}")
    
    # Sort results by relevance or price
    # First put cross-chain products at the top, then sort by price within each group
    grouped_products.sort(key=lambda p: (
        0 if p.get('cross_chain', False) else 1,  # Cross-chain products first
        p.get('prices', [{}])[0].get('price', 999999) if isinstance(p.get('prices', []), list) and p.get('prices', []) else p.get('price', p.get('item_price', 999999))
    ))
    
    print("Finished sorting grouped products")
    return grouped_products
    
    # Add remaining products that don't have valid item codes
    for product in products:
        item_code = product.get('item_code')
        # If product doesn't have a valid item code or it hasn't been processed yet, add it
        if not item_code or str(item_code).strip() in ('0', '') or str(item_code).strip() not in processed_item_codes:
            grouped_products.append(product)
            if item_code and str(item_code).strip() not in ('0', ''):
                processed_item_codes.add(str(item_code).strip())
    
    # Sort results by relevance or price
    # First put cross-chain products at the top, then sort by price within each group
    grouped_products.sort(key=lambda p: (
        0 if p.get('cross_chain', False) else 1,  # Cross-chain products first
        p.get('prices', [{}])[0].get('price', 999999) if isinstance(p.get('prices', []), list) and p.get('prices', []) else p.get('price', p.get('item_price', 999999))
    ))
    
    return grouped_products