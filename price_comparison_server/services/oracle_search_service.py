"""
Oracle-Compatible Search Service Module
Version 3.0

Updated search implementation that works with Oracle Autonomous Database
using SQLAlchemy ORM instead of direct SQLite queries.
"""

import os
import sys
import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

# Add project root to path for imports if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.models import Store, Price
from utils.product_utils import extract_product_weight, get_price_per_unit, generate_cross_chain_comparison

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============= Configuration =============

class QueryType(Enum):
    SHORT_TERM = "short_term"
    GENERAL = "general"
    WITH_WEIGHT = "with_weight"
    BRAND_SPECIFIC = "brand_specific"

# Product categories and their terms
PRODUCT_CATEGORIES = {
    'dairy': ['חלב', 'גבינה', 'קוטג', 'יוגורט', 'משקה חלב', 'שמנת', 'חמאה', 'לבן'],
    'snack': ['במבה', 'ביסלי', 'דובונים', 'אפרופו', 'תפוציפס', 'חטיף', 'פופקורן'],
    'bread': ['לחם', 'פיתות', 'לחמניות', 'בייגל', 'חלה'],
    'sweets': ['שוקולד', 'ממתק', 'סוכריות', 'גומי', 'דובדבן', 'עוגה', 'עוגיות'],
    'beverages': ['משקה', 'שתיה', 'קולה', 'מים', 'יין', 'בירה', 'מיץ'],
    'meat': ['בשר', 'עוף', 'הודו', 'כבש', 'דג'],
    'cleaning': ['ניקוי', 'סבון', 'אקונומיקה', 'מרכך'],
}

# Short term expansions
SHORT_TERM_EXPANSIONS = {
    'דוב': ['דובונים', 'דובדבן', 'דובים', 'סוכריות גומי', 'דובוני'],
    'במב': ['במבה', 'במבה נוגט', 'במבה מתוקה', 'חטיף במבה'],
    'במ': ['במבה', 'במבה נוגט', 'במבה מתוקה'],
    'ביס': ['ביסלי', 'ביסלי גריל', 'ביסלי פיצה', 'ביסלי בצל'],
    'חל': ['חלב', 'חלבי', 'חלב טרי', 'משקה חלב'],
    'גב': ['גבינה', 'גבינת', 'גבינה לבנה', 'גבינה צהובה'],
    'תה': ['תה', 'משקה תה', 'שתיה חמה', 'תה צמחים'],
    'קוק': ['קוקה', 'קולה', 'קוקה קולה', 'קוקה זירו'],
    'שוק': ['שוקולד', 'שוקו', 'שוקולד חלב', 'שוקולד מריר'],
}

# Search configuration
MAX_STORES_PER_CHAIN = 10  # Increased for better coverage
MAX_RESULTS_PER_SEARCH = 500  # Total results limit
DEFAULT_RESULT_LIMIT = 100

# ============= Data Classes =============

@dataclass
class QueryInfo:
    """Parsed query information"""
    original_query: str
    query_type: QueryType
    category: Optional[str] = None
    weight_value: Optional[float] = None
    weight_unit: Optional[str] = None
    expansion_terms: List[str] = None
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.expansion_terms is None:
            self.expansion_terms = []
        if self.keywords is None:
            self.keywords = []

@dataclass
class SearchResult:
    """Individual search result from database"""
    item_name: str
    item_code: str
    chain: str
    store_id: str
    city: str
    price: float
    timestamp: str
    relevance_score: float = 0.0
    weight: Optional[float] = None
    unit: Optional[str] = None
    price_per_unit: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        result = {
            'item_name': self.item_name,
            'item_code': self.item_code,
            'chain': self.chain,
            'store_id': self.store_id,
            'price': self.price,
            'timestamp': self.timestamp,
            'relevance_score': self.relevance_score
        }
        
        # Add optional fields
        if self.weight is not None:
            result['weight'] = self.weight
        if self.unit is not None:
            result['unit'] = self.unit
        if self.price_per_unit is not None:
            result['price_per_unit'] = self.price_per_unit
            
        return result

# ============= Query Parsing =============

def parse_query(query: str) -> QueryInfo:
    """Parse a search query into structured information"""
    if not query:
        return QueryInfo(
            original_query="",
            query_type=QueryType.GENERAL,
            keywords=[]
        )
    
    query = query.strip()
    query_lower = query.lower()
    
    # Determine query type
    if len(query) <= 3:
        query_type = QueryType.SHORT_TERM
    elif extract_product_weight(query)[0] is not None:
        query_type = QueryType.WITH_WEIGHT
    else:
        query_type = QueryType.GENERAL
    
    # Extract category
    category = None
    for cat, terms in PRODUCT_CATEGORIES.items():
        if any(term in query_lower for term in terms):
            category = cat
            break
    
    # Get expansion terms for short queries
    expansion_terms = []
    if query_type == QueryType.SHORT_TERM:
        for key, expansions in SHORT_TERM_EXPANSIONS.items():
            if key in query_lower:
                expansion_terms.extend(expansions)
                break
        
        # If no specific expansion found, add generic expansions
        if not expansion_terms and len(query) <= 3:
            expansion_terms = [query, f"{query}ים", f"{query}ות"]
    
    # Extract weight/volume
    weight_value, weight_unit = extract_product_weight(query)
    
    # Extract keywords
    keywords = [word for word in query.split() if len(word) > 1]
    
    return QueryInfo(
        original_query=query,
        query_type=query_type,
        category=category,
        weight_value=weight_value,
        weight_unit=weight_unit,
        expansion_terms=expansion_terms,
        keywords=keywords
    )

# ============= Relevance Scoring =============

def calculate_relevance_score(product_name: str, query_info: QueryInfo, 
                            has_price_per_unit: bool = False) -> float:
    """Calculate relevance score for a product based on the query"""
    score = 0.0
    product_lower = product_name.lower()
    query_lower = query_info.original_query.lower()
    
    # Exact match
    if query_lower == product_lower:
        score += 100.0
    # Product starts with query
    elif product_lower.startswith(query_lower):
        score += 80.0
    # Query as complete word
    elif f' {query_lower} ' in f' {product_lower} ':
        score += 60.0
    # Query contained in product
    elif query_lower in product_lower:
        score += 40.0
    
    # Check expansion terms
    if query_info.expansion_terms:
        for term in query_info.expansion_terms:
            if term.lower() in product_lower:
                score += 30.0
                break
    
    # Keyword matches
    if query_info.keywords:
        keyword_matches = sum(1 for kw in query_info.keywords if kw.lower() in product_lower)
        score += keyword_matches * 10.0
    
    # Category bonus
    if query_info.category:
        category_terms = PRODUCT_CATEGORIES.get(query_info.category, [])
        if any(term in product_lower for term in category_terms):
            score += 15.0
    
    # Weight match bonus
    if query_info.weight_value and query_info.weight_unit:
        product_weight, product_unit = extract_product_weight(product_name)
        if product_weight and product_unit == query_info.weight_unit:
            if abs(product_weight - query_info.weight_value) < 0.01:
                score += 25.0  # Exact weight match
            elif abs(product_weight - query_info.weight_value) / query_info.weight_value < 0.1:
                score += 15.0  # Close weight match
    
    # Bonus for price per unit
    if has_price_per_unit:
        score += 5.0
    
    return score

# ============= Database Search Functions =============

def search_in_database(db: Session, city: str, query_info: QueryInfo, 
                      limit: int = MAX_RESULTS_PER_SEARCH) -> List[SearchResult]:
    """
    Search for products in the database using SQLAlchemy ORM
    """
    results = []
    
    # Build search conditions
    search_conditions = []
    
    # Add patterns for the original query
    query = query_info.original_query
    search_conditions.extend([
        Price.item_name.like(f'{query}%'),      # Starts with
        Price.item_name.like(f'% {query} %'),   # Word match
        Price.item_name.like(f'% {query}%'),    # Word at start
        Price.item_name.like(f'%{query}%'),     # Contains
    ])
    
    # Add expansion terms for short queries
    if query_info.expansion_terms:
        for term in query_info.expansion_terms:
            search_conditions.append(Price.item_name.like(f'%{term}%'))
    
    # Create the main query
    query = db.query(Price, Store).join(Store).filter(
        Store.city == city,
        or_(*search_conditions)
    ).limit(limit)
    
    # Execute query
    try:
        db_results = query.all()
        
        for price, store in db_results:
            # Calculate price per unit
            price_info = get_price_per_unit(price.item_name, price.item_price)
            
            result = SearchResult(
                item_name=price.item_name,
                item_code=price.item_code or '',
                chain=store.chain,
                store_id=store.snif_key,
                city=store.city,
                price=float(price.item_price),
                timestamp=price.timestamp.isoformat() if price.timestamp else '',
                weight=price_info['value'] if price_info else None,
                unit=price_info['unit'] if price_info else None,
                price_per_unit=price_info['price_per_unit'] if price_info else None
            )
            
            # Calculate relevance score
            result.relevance_score = calculate_relevance_score(
                result.item_name,
                query_info,
                result.price_per_unit is not None
            )
            
            results.append(result)
            
    except Exception as e:
        logger.error(f"Database search error: {str(e)}")
    
    return results

def group_products_by_item_code(products: List[SearchResult]) -> List[Dict[str, Any]]:
    """
    Group products by item code to identify identical products across stores
    This includes products in different stores of the same chain
    """
    # Group by item code
    item_code_groups = defaultdict(list)
    products_without_code = []

    for product in products:
        if product.item_code and product.item_code.strip() not in ('0', ''):
            item_code_groups[product.item_code.strip()].append(product)
        else:
            products_without_code.append(product)

    logger.info(f"Grouping {len(products)} products into {len(item_code_groups)} item code groups")

    grouped_results = []

    # Process products with same item code
    for item_code, group_products in item_code_groups.items():
        # Get unique stores for this product
        unique_stores = set()
        chains = set()
        for p in group_products:
            unique_stores.add(f"{p.chain}:{p.store_id}")
            chains.add(p.chain)

        # If product appears in multiple stores OR multiple chains
        if len(unique_stores) > 1:
            logger.debug(f"Multi-store product {item_code} found in {len(unique_stores)} stores across {len(chains)} chains")

            # Choose best product name (highest relevance score)
            base_product = max(group_products, key=lambda p: p.relevance_score)

            merged_product = {
                'item_name': base_product.item_name,
                'item_code': item_code,
                'prices': [],
                'cross_chain': len(chains) > 1,  # True only if multiple chains
                'multi_store': True,  # True if multiple stores (same or different chains)
                'store_count': len(unique_stores),
                'chain_count': len(chains),
                'relevance_score': max(p.relevance_score for p in group_products)
            }

            # Add all prices from all stores
            seen_stores = set()
            for product in group_products:
                store_key = f"{product.chain}:{product.store_id}"
                # Avoid duplicates from the same store
                if store_key not in seen_stores:
                    seen_stores.add(store_key)
                    merged_product['prices'].append({
                        'chain': product.chain,
                        'store_id': product.store_id,
                        'price': product.price,
                        'original_name': product.item_name,
                        'timestamp': product.timestamp,
                        'city': product.city
                    })

            # Sort prices (lowest first)
            merged_product['prices'].sort(key=lambda p: p['price'])

            # Add price comparison data
            if len(merged_product['prices']) > 1:
                lowest_price = merged_product['prices'][0]
                highest_price = merged_product['prices'][-1]

                savings = highest_price['price'] - lowest_price['price']
                savings_percent = (savings / highest_price['price']) * 100 if highest_price['price'] > 0 else 0

                merged_product['price_comparison'] = {
                    'best_deal': {
                        'chain': lowest_price['chain'],
                        'store_id': lowest_price['store_id'],
                        'price': lowest_price['price'],
                        'city': lowest_price.get('city', '')
                    },
                    'worst_deal': {
                        'chain': highest_price['chain'],
                        'store_id': highest_price['store_id'],
                        'price': highest_price['price'],
                        'city': highest_price.get('city', '')
                    },
                    'savings': savings,
                    'savings_percent': savings_percent,
                    'price_range': {
                        'min': lowest_price['price'],
                        'max': highest_price['price'],
                        'avg': sum(p['price'] for p in merged_product['prices']) / len(merged_product['prices'])
                    }
                }

            # Copy optional attributes from base product
            if base_product.price_per_unit is not None:
                merged_product['price_per_unit'] = base_product.price_per_unit
            if base_product.unit is not None:
                merged_product['unit'] = base_product.unit
            if base_product.weight is not None:
                merged_product['weight'] = base_product.weight

            grouped_results.append(merged_product)
        else:
            # Single store product - add individually
            for product in group_products:
                result_dict = product.to_dict()
                result_dict['multi_store'] = False
                result_dict['store_count'] = 1
                result_dict['chain_count'] = 1
                grouped_results.append(result_dict)

    # Add products without codes
    for product in products_without_code:
        result_dict = product.to_dict()
        result_dict['multi_store'] = False
        result_dict['store_count'] = 1
        result_dict['chain_count'] = 1
        grouped_results.append(result_dict)

    # Sort results: multi-store products first, then by relevance
    grouped_results.sort(key=lambda p: (
        -1 if p.get('multi_store', False) else 0,
        -p.get('store_count', 1),  # More stores = higher priority
        -p.get('relevance_score', 0)
    ))

    logger.info(f"Grouped results: {len([r for r in grouped_results if r.get('multi_store')])} multi-store products")
    
    return grouped_results

def balance_results(results: List[SearchResult], limit: int = DEFAULT_RESULT_LIMIT) -> List[Dict[str, Any]]:
    """Balance results between chains for fair representation"""
    # Group by chain
    chain_results = defaultdict(list)
    for result in results:
        chain_results[result.chain].append(result)
    
    # Sort each chain's results by relevance
    for chain in chain_results:
        chain_results[chain].sort(key=lambda x: x.relevance_score, reverse=True)
    
    balanced = []
    
    # Ensure minimum representation from each chain
    chains = list(chain_results.keys())
    if not chains:
        return []
        
    min_per_chain = min(10, limit // len(chains))
    
    # First pass: minimum from each chain
    for chain in chains:
        for result in chain_results[chain][:min_per_chain]:
            balanced.append(result.to_dict())
    
    # Fill remaining slots
    remaining_slots = limit - len(balanced)
    chain_indices = {chain: min_per_chain for chain in chains}
    
    while len(balanced) < limit:
        added_any = False
        
        for chain in chains:
            if chain_indices[chain] < len(chain_results[chain]):
                result = chain_results[chain][chain_indices[chain]]
                balanced.append(result.to_dict())
                chain_indices[chain] += 1
                added_any = True
                
                if len(balanced) >= limit:
                    break
        
        if not added_any:
            break
    
    return balanced[:limit]

# ============= Main Search Function =============

def search_products_by_name_and_city_with_db(db: Session, city: str, item_name: str, 
                                    group_by_code: bool = False) -> List[Dict[str, Any]]:
    """
    Main search function with Oracle database support
    
    Args:
        db: SQLAlchemy database session
        city: City to search in
        item_name: Product name to search for
        group_by_code: Whether to group results by item code
        
    Returns:
        List of product dictionaries with search results
    """
    try:
        logger.info(f"=== Search request: '{item_name}' in '{city}', group_by_code: {group_by_code} ===")
        
        # Parse query
        query_info = parse_query(item_name)
        logger.info(f"Query parsed - Type: {query_info.query_type.value}, Category: {query_info.category}")
        
        # Search in database
        results = search_in_database(db, city, query_info)
        logger.info(f"Found {len(results)} results")
        
        if not results:
            return []
        
        # Apply grouping or balancing
        if group_by_code:
            logger.info("Grouping products by item code...")
            final_results = group_products_by_item_code(results)
            logger.info(f"Returning {len(final_results)} grouped results")
        else:
            # Balance results between chains
            final_results = balance_results(results)
            logger.info(f"Returning {len(final_results)} balanced results")
        
        return final_results
        
    except Exception as e:
        logger.error(f"Error in search: {str(e)}", exc_info=True)
        return []

# ============= Backward Compatibility =============

# For backward compatibility with old function signatures
def search_products_by_name_and_city(city: str, item_name: str, 
                                    group_by_code: bool = False) -> List[Dict[str, Any]]:
    """
    Backward compatibility wrapper for routes that don't pass db session
    """
    from database.connection import get_db
    
    with get_db() as db:
        return search_products_by_name_and_city(db, city, item_name, group_by_code)

# ============= Cheapest Cart Calculation =============

def calculate_cheapest_cart(db: Session, city: str, cart_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate the cheapest cart across all stores in a city
    
    Args:
        db: Database session
        city: City to search in
        cart_items: List of items with 'item_name' and 'quantity'
        
    Returns:
        Dictionary with cheapest store info and prices
    """
    try:
        logger.info(f"Calculating cheapest cart for {len(cart_items)} items in {city}")
        
        # Get all stores in the city
        stores = db.query(Store).filter(Store.city == city).all()
        logger.info(f"Found {len(stores)} stores in {city}")
        
        if not stores:
            raise ValueError(f"No stores found in {city}")
        
        # Track prices for each store
        store_totals = {}
        store_items = defaultdict(dict)
        
        # Search for each item
        for cart_item in cart_items:
            item_name = cart_item['item_name']
            quantity = cart_item['quantity']
            
            # Parse query for better matching
            query_info = parse_query(item_name)
            
            # Search for this item in all stores
            search_conditions = []
            search_conditions.extend([
                Price.item_name.like(f'{item_name}%'),
                Price.item_name.like(f'% {item_name} %'),
                Price.item_name.like(f'%{item_name}%'),
            ])
            
            # Add expansion terms
            if query_info.expansion_terms:
                for term in query_info.expansion_terms:
                    search_conditions.append(Price.item_name.like(f'%{term}%'))
            
            # Query for this item across all stores in the city
            item_results = db.query(Price, Store).join(Store).filter(
                Store.city == city,
                or_(*search_conditions)
            ).all()
            
            # Group by store and find best price for this item in each store
            for price, store in item_results:
                store_key = f"{store.chain}:{store.snif_key}"
                
                # Calculate relevance score
                relevance = calculate_relevance_score(price.item_name, query_info)
                
                # Only consider items with reasonable relevance
                if relevance < 20:
                    continue
                
                # Track best match for this item in this store
                if store_key not in store_items[item_name]:
                    store_items[item_name][store_key] = {
                        'price': price.item_price,
                        'relevance': relevance,
                        'product_name': price.item_name
                    }
                elif relevance > store_items[item_name][store_key]['relevance']:
                    store_items[item_name][store_key] = {
                        'price': price.item_price,
                        'relevance': relevance,
                        'product_name': price.item_name
                    }
        
        # Calculate totals for stores that have all items
        complete_stores = []
        
        for store in stores:
            store_key = f"{store.chain}:{store.snif_key}"
            has_all_items = True
            total_price = 0.0
            items_found = []
            
            for cart_item in cart_items:
                item_name = cart_item['item_name']
                quantity = cart_item['quantity']
                
                if store_key in store_items.get(item_name, {}):
                    item_info = store_items[item_name][store_key]
                    item_total = item_info['price'] * quantity
                    total_price += item_total
                    items_found.append({
                        'requested': item_name,
                        'found': item_info['product_name'],
                        'price': item_info['price'],
                        'quantity': quantity,
                        'total': item_total
                    })
                else:
                    has_all_items = False
                    break
            
            if has_all_items:
                complete_stores.append({
                    'chain': store.chain,
                    'store_id': store.snif_key,
                    'store_name': store.store_name,
                    'total_price': total_price,
                    'items': items_found
                })
        
        if not complete_stores:
            logger.warning("No stores have all requested items")
            return {
                'error': 'Could not find all items in any single store',
                'city': city,
                'items_requested': cart_items
            }
        
        # Sort by total price
        complete_stores.sort(key=lambda x: x['total_price'])
        
        # Get best and worst for savings calculation
        best_store = complete_stores[0]
        worst_store = complete_stores[-1]
        
        savings = worst_store['total_price'] - best_store['total_price']
        savings_percent = (savings / worst_store['total_price']) * 100 if worst_store['total_price'] > 0 else 0
        
        return {
            'chain': best_store['chain'],
            'store_id': best_store['store_id'],
            'store_name': best_store['store_name'],
            'total_price': best_store['total_price'],
            'worst_price': worst_store['total_price'],
            'savings': savings,
            'savings_percent': savings_percent,
            'city': city,
            'items': best_store['items'],
            'all_stores': complete_stores[:10]  # Top 10 stores
        }
        
    except Exception as e:
        logger.error(f"Error calculating cheapest cart: {str(e)}", exc_info=True)
        return {
            'error': str(e),
            'city': city,
            'items_requested': cart_items
        }
