"""
Enhanced Search Service Module - Complete Rewrite
Version 2.0

A cleaner, more robust implementation with better error handling,
improved performance, and all the enhanced features.
"""

import os
import sqlite3
import sys
import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

# Add project root to path for imports if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.db_utils import get_db_connection, get_corrected_city_path, DBS
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

# Emergency fallback cities for Victory
FALLBACK_CITIES = ['Tel Aviv', 'Jerusalem', 'Haifa', 'Beer Sheva', 'Netanya']

# Search configuration
MAX_STORES_PER_CHAIN = 5
MAX_RESULTS_PER_STORE = 100
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
    """Individual search result"""
    item_name: str
    item_code: str
    chain: str
    store_id: str
    price: float
    timestamp: str
    relevance_score: float = 0.0
    weight: Optional[float] = None
    unit: Optional[str] = None
    price_per_unit: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        result = {
            'item_name': self.item_name,
            'item_code': self.item_code,
            'chain': self.chain,
            'store_id': self.store_id,
            'price': self.price,
            'timestamp': self.timestamp,
            'relevance_score': self.relevance_score
        }
        
        # Add optional fields only if they have values
        if self.weight is not None:
            result['weight'] = self.weight
        if self.unit is not None:
            result['unit'] = self.unit
        if self.price_per_unit is not None:
            result['price_per_unit'] = self.price_per_unit
            
        return result

# ============= Query Parsing =============

def parse_query(query: str) -> QueryInfo:
    """
    Parse a search query into structured information.
    Enhanced with better pattern recognition and error handling.
    """
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
        
        # If no specific expansion found, try to be smart about it
        if not expansion_terms and len(query) <= 3:
            # Add the query itself with common suffixes
            expansion_terms = [query, f"{query}ים", f"{query}ות"]
    
    # Extract weight/volume
    weight_value, weight_unit = extract_product_weight(query)
    
    # Extract keywords (remove very short words)
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
    """
    Calculate relevance score for a product based on the query.
    Returns a score from 0 to 100+.
    """
    score = 0.0
    product_lower = product_name.lower()
    query_lower = query_info.original_query.lower()
    
    # Exact match is best
    if query_lower == product_lower:
        score += 100.0
    # Product name starts with query
    elif product_lower.startswith(query_lower):
        score += 80.0
    # Query as complete word in product name
    elif f' {query_lower} ' in f' {product_lower} ':
        score += 60.0
    # Query contained in product name
    elif query_lower in product_lower:
        score += 40.0
    
    # Check expansion terms (for short queries)
    if query_info.expansion_terms:
        for term in query_info.expansion_terms:
            if term.lower() in product_lower:
                score += 30.0
                break
    
    # Keyword matches
    if query_info.keywords:
        keyword_matches = sum(1 for kw in query_info.keywords if kw.lower() in product_lower)
        score += keyword_matches * 10.0
    
    # Category match bonus
    if query_info.category:
        category_terms = PRODUCT_CATEGORIES.get(query_info.category, [])
        if any(term in product_lower for term in category_terms):
            score += 15.0
    
    # Weight match bonus (if query has weight)
    if query_info.weight_value and query_info.weight_unit:
        product_weight, product_unit = extract_product_weight(product_name)
        if product_weight and product_unit == query_info.weight_unit:
            if abs(product_weight - query_info.weight_value) < 0.01:
                score += 25.0  # Exact weight match
            elif abs(product_weight - query_info.weight_value) / query_info.weight_value < 0.1:
                score += 15.0  # Close weight match (within 10%)
    
    # Bonus for products with calculable price per unit
    if has_price_per_unit:
        score += 5.0
    
    return score

# ============= Search Pattern Generation =============

def generate_search_patterns(query_info: QueryInfo) -> List[str]:
    """Generate SQL LIKE patterns for searching."""
    patterns = []
    query = query_info.original_query
    
    if query_info.query_type == QueryType.SHORT_TERM:
        # For short terms, use broader patterns
        patterns.append(f'%{query}%')
        
        # Add expansion patterns
        for term in query_info.expansion_terms:
            patterns.append(f'%{term}%')
            
    else:
        # Standard patterns for longer queries
        patterns.extend([
            f'{query}%',       # Starts with
            f'% {query} %',    # Exact word (with spaces)
            f'% {query}%',     # Word at beginning  
            f'%{query}%',      # Contains anywhere
        ])
        
        # Add patterns for individual keywords if multi-word query
        if len(query_info.keywords) > 1:
            for keyword in query_info.keywords:
                if len(keyword) > 2:  # Skip very short keywords
                    patterns.append(f'%{keyword}%')
    
    # Remove duplicates while preserving order
    seen = set()
    unique_patterns = []
    for pattern in patterns:
        if pattern not in seen:
            seen.add(pattern)
            unique_patterns.append(pattern)
    
    return unique_patterns

# ============= Database Search Functions =============

def search_in_store(chain: str, city: str, store_id: str, 
                   patterns: List[str]) -> List[SearchResult]:
    """
    Search for products in a specific store.
    Returns list of SearchResult objects.
    """
    results = []
    
    try:
        conn = get_db_connection(chain, city, store_id)
        cursor = conn.cursor()
        
        # Track items we've already added to avoid duplicates
        seen_items = set()
        
        for pattern in patterns:
            cursor.execute(
                """SELECT item_code, item_name, item_price, timestamp 
                   FROM prices 
                   WHERE item_name LIKE ? 
                   LIMIT ?""",
                (pattern, MAX_RESULTS_PER_STORE)
            )
            rows = cursor.fetchall()
            
            for row in rows:
                item_key = (row['item_name'], row['item_code'])
                if item_key not in seen_items:
                    seen_items.add(item_key)
                    
                    # Create SearchResult
                    result = SearchResult(
                        item_name=row['item_name'],
                        item_code=row['item_code'] or '',
                        chain=chain,
                        store_id=store_id,
                        price=float(row['item_price']),
                        timestamp=row['timestamp']
                    )
                    
                    # Calculate price per unit if possible
                    price_info = get_price_per_unit(result.item_name, result.price)
                    if price_info:
                        result.price_per_unit = price_info['price_per_unit']
                        result.unit = price_info['unit']
                        result.weight = price_info['value']
                    
                    results.append(result)
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error searching {chain}/{city}/{store_id}: {str(e)}")
    
    return results

def search_chain(chain: str, city: str, patterns: List[str], 
                limit_stores: int = MAX_STORES_PER_CHAIN) -> List[SearchResult]:
    """Search all stores in a chain within a city."""
    all_results = []
    
    # Get city path
    city_path = get_corrected_city_path(DBS[chain], city)
    if not city_path or not os.path.exists(city_path):
        logger.warning(f"City path not found for {chain}/{city}")
        return all_results
    
    # Get store files
    store_files = [f for f in os.listdir(city_path) if f.endswith('.db')]
    if not store_files:
        logger.warning(f"No stores found in {chain}/{city}")
        return all_results
    
    # Search stores
    stores_searched = 0
    for store_file in store_files[:limit_stores]:
        store_id = store_file[:-3]  # Remove .db extension
        store_results = search_in_store(chain, city, store_id, patterns)
        all_results.extend(store_results)
        stores_searched += 1
        
        # Stop if we have enough results
        if len(all_results) >= MAX_RESULTS_PER_STORE * 2:
            break
    
    logger.debug(f"Searched {stores_searched} stores in {chain}/{city}, found {len(all_results)} results")
    return all_results

def apply_victory_fallback(patterns: List[str], query_info: QueryInfo) -> List[SearchResult]:
    """Apply Victory fallback search when no results found in requested city."""
    logger.info(f"Applying Victory fallback for query: {query_info.original_query}")
    
    for fallback_city in FALLBACK_CITIES:
        results = search_chain('victory', fallback_city, patterns, limit_stores=2)
        if results:
            logger.info(f"Found {len(results)} Victory results in fallback city: {fallback_city}")
            return results[:20]  # Return limited results from fallback
    
    return []

# ============= Result Processing =============

def group_products_by_item_code(products: List[SearchResult]) -> List[Dict[str, Any]]:
    """
    Group products by item code to identify identical products across chains.
    Returns list of grouped products with cross-chain information.
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
        chains = set(p.chain for p in group_products)
        
        if len(chains) > 1:
            # Cross-chain product
            logger.debug(f"Cross-chain product {item_code} found in: {chains}")
            
            # Choose best product name (prefer Shufersal)
            base_product = next(
                (p for p in group_products if p.chain == 'shufersal'),
                max(group_products, key=lambda p: p.relevance_score)
            )
            
            merged_product = {
                'item_name': base_product.item_name,
                'item_code': item_code,
                'prices': [],
                'cross_chain': True,
                'relevance_score': max(p.relevance_score for p in group_products)
            }
            
            # Add all prices
            for product in group_products:
                merged_product['prices'].append({
                    'chain': product.chain,
                    'store_id': product.store_id,
                    'price': product.price,
                    'original_name': product.item_name,
                    'timestamp': product.timestamp
                })
            
            # Sort prices by price
            merged_product['prices'].sort(key=lambda p: p['price'])
            
            # Add price comparison
            comparison = generate_cross_chain_comparison(merged_product)
            if comparison:
                merged_product['price_comparison'] = comparison
            
            # Copy optional attributes safely
            if base_product.price_per_unit is not None:
                merged_product['price_per_unit'] = base_product.price_per_unit
            if base_product.unit is not None:
                merged_product['unit'] = base_product.unit
            if base_product.weight is not None:
                merged_product['weight'] = base_product.weight
            
            grouped_results.append(merged_product)
        else:
            # Single chain products - add individually
            for product in group_products:
                grouped_results.append(product.to_dict())
    
    # Add products without codes
    for product in products_without_code:
        grouped_results.append(product.to_dict())
    
    # Sort results: cross-chain first, then by relevance
    grouped_results.sort(key=lambda p: (
        -1 if p.get('cross_chain', False) else 0,
        -p.get('relevance_score', 0)
    ))
    
    return grouped_results

def balance_results(chain_results: Dict[str, List[SearchResult]], 
                   limit: int = DEFAULT_RESULT_LIMIT) -> List[Dict[str, Any]]:
    """
    Balance results between chains for fair representation.
    Returns list of dictionaries.
    """
    # Sort each chain's results by relevance
    for chain in chain_results:
        chain_results[chain].sort(key=lambda x: x.relevance_score, reverse=True)
    
    balanced = []
    
    # Ensure minimum representation from each chain
    min_per_chain = min(10, limit // len(chain_results) if chain_results else 10)
    
    for chain in chain_results:
        for result in chain_results[chain][:min_per_chain]:
            balanced.append(result.to_dict())
    
    # Fill remaining slots using round-robin
    remaining_slots = limit - len(balanced)
    chain_indices = {chain: min_per_chain for chain in chain_results}
    
    while len(balanced) < limit:
        added_any = False
        
        for chain in chain_results:
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

def search_products_by_name_and_city(city: str, item_name: str, 
                                    group_by_code: bool = False) -> List[Dict[str, Any]]:
    """
    Main search function with enhanced features and error handling.
    
    Args:
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
        
        # Generate search patterns
        patterns = generate_search_patterns(query_info)
        logger.debug(f"Generated {len(patterns)} search patterns")
        
        # Search both chains
        all_results = []
        chain_results = {}
        
        for chain in ['shufersal', 'victory']:
            logger.info(f"Searching {chain} chain...")
            results = search_chain(chain, city, patterns)
            
            # Apply Victory fallback if needed
            if chain == 'victory' and len(results) < 5:
                fallback_results = apply_victory_fallback(patterns, query_info)
                results.extend(fallback_results)
            
            # Calculate relevance scores
            for result in results:
                result.relevance_score = calculate_relevance_score(
                    result.item_name,
                    query_info,
                    result.price_per_unit is not None
                )
            
            chain_results[chain] = results
            all_results.extend(results)
            logger.info(f"Found {len(results)} results in {chain}")
        
        # Apply grouping or balancing
        if group_by_code:
            logger.info("Grouping products by item code...")
            final_results = group_products_by_item_code(all_results)
            logger.info(f"Returning {len(final_results)} grouped results")
        else:
            # Balance results between chains
            final_results = balance_results(chain_results)
            logger.info(f"Returning {len(final_results)} balanced results")
        
        return final_results
        
    except Exception as e:
        logger.error(f"Error in search: {str(e)}", exc_info=True)
        return []

# ============= Backward Compatibility =============
# Replace the entire backward compatibility section at the end of search_service.py with this:

def balance_results_enhanced(chain_results: Dict[str, List[Dict[str, Any]]], 
                           query_info: Dict[str, Any], 
                           limit: int = DEFAULT_RESULT_LIMIT) -> List[Dict[str, Any]]:
    """Backward compatibility wrapper - not used anymore but kept for compatibility."""
    # If we get a dict of lists (expected format)
    if isinstance(chain_results, dict):
        # Convert any dict items to SearchResult objects for balance_results
        converted_results = {}
        for chain, results in chain_results.items():
            converted_results[chain] = []
            for r in results:
                if isinstance(r, dict):
                    result = SearchResult(
                        item_name=r.get('item_name', ''),
                        item_code=r.get('item_code', ''),
                        chain=r.get('chain', chain),
                        store_id=r.get('store_id', ''),
                        price=r.get('price', r.get('item_price', 0)),
                        timestamp=r.get('timestamp', ''),
                        relevance_score=r.get('relevance_score', 0)
                    )
                    converted_results[chain].append(result)
                elif isinstance(r, SearchResult):
                    converted_results[chain].append(r)
        
        return balance_results(converted_results, limit)
    
    # If we somehow get a list, convert it
    elif isinstance(chain_results, list):
        # Group by chain first
        chain_grouped = {}
        for item in chain_results:
            chain = item.get('chain', 'unknown') if isinstance(item, dict) else item.chain
            if chain not in chain_grouped:
                chain_grouped[chain] = []
            
            if isinstance(item, dict):
                result = SearchResult(
                    item_name=item.get('item_name', ''),
                    item_code=item.get('item_code', ''),
                    chain=chain,
                    store_id=item.get('store_id', ''),
                    price=item.get('price', item.get('item_price', 0)),
                    timestamp=item.get('timestamp', ''),
                    relevance_score=item.get('relevance_score', 0)
                )
                chain_grouped[chain].append(result)
            else:
                chain_grouped[chain].append(item)
                
        return balance_results(chain_grouped, limit)
    
    return []

# For backward compatibility - old function that might be called from price_routes.py
def balance_results(results: Any, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Backward compatibility function for old balance_results calls.
    Handles both the new format (dict of SearchResult lists) and old format (flat list).
    """
    if not results:
        return []
    
    # Case 1: It's already a list of dicts (old format from routes)
    if isinstance(results, list):
        # Just limit and return
        return results[:limit]
    
    # Case 2: It's a dict of SearchResult lists (new internal format)
    elif isinstance(results, dict):
        # Check if values are lists of SearchResult objects
        first_key = next(iter(results.keys())) if results else None
        if first_key and results[first_key] and isinstance(results[first_key], list):
            # Use the proper balance_results logic for dict of SearchResult lists
            balanced = []
            
            # Ensure minimum representation from each chain
            min_per_chain = min(10, limit // len(results) if results else 10)
            
            for chain, chain_results in results.items():
                # Convert SearchResult objects to dicts
                for i, result in enumerate(chain_results[:min_per_chain]):
                    if hasattr(result, 'to_dict'):
                        balanced.append(result.to_dict())
                    elif isinstance(result, dict):
                        balanced.append(result)
                    
                    if len(balanced) >= limit:
                        break
            
            # Fill remaining slots using round-robin
            remaining_slots = limit - len(balanced)
            if remaining_slots > 0:
                chain_indices = {chain: min_per_chain for chain in results}
                
                while len(balanced) < limit:
                    added_any = False
                    
                    for chain, chain_results in results.items():
                        if chain_indices[chain] < len(chain_results):
                            result = chain_results[chain_indices[chain]]
                            if hasattr(result, 'to_dict'):
                                balanced.append(result.to_dict())
                            elif isinstance(result, dict):
                                balanced.append(result)
                            chain_indices[chain] += 1
                            added_any = True
                            
                            if len(balanced) >= limit:
                                break
                    
                    if not added_any:
                        break
            
            return balanced[:limit]
    
    # Fallback - try to convert whatever we have to a list
    try:
        return list(results)[:limit]
    except:
        return []