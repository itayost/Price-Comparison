import re
from typing import Tuple, Dict, Optional, Any, List

def extract_product_weight(item_name: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Extracts weight or volume information from product names.
    Returns a tuple of (value, unit) or (None, None) if not found.
    """
    # Common units in Hebrew product descriptions
    units = {
        'גרם': 'g',
        'ג': 'g',
        'גר': 'g',
        "ג'": 'g',
        'קג': 'kg', 
        'ק"ג': 'kg',
        'קילו': 'kg',
        'ליטר': 'l',
        'ל': 'l',
        'מל': 'ml',
        'מ"ל': 'ml',
        'יחידות': 'unit'
    }
    
    # Pattern to match number + unit
    pattern = r'(\d+(?:\.\d+)?)\s*(' + '|'.join(units.keys()) + r')'
    matches = re.findall(pattern, item_name)
    
    if matches:
        value, unit = matches[0]
        return (float(value), units[unit])
    
    # Try to match common formats like "80g" without space
    compact_pattern = r'(\d+(?:\.\d+)?)(' + '|'.join(['ג', 'גר', 'קג', 'ל', 'מל']) + r')'
    matches = re.findall(compact_pattern, item_name)
    
    if matches:
        value, unit = matches[0]
        return (float(value), units[unit])
        
    return (None, None)

def get_price_per_unit(item_name: str, price: float) -> Optional[Dict[str, Any]]:
    """
    Calculate the price per unit (gram, ml, etc) to enable comparison
    between different package sizes.
    """
    value, unit = extract_product_weight(item_name)
    
    if value is None or value == 0:
        return None
        
    # Convert to base unit (g, ml)
    if unit == 'kg':
        value = value * 1000
        unit = 'g'
    elif unit == 'l':
        value = value * 1000
        unit = 'ml'
        
    return {
        'price_per_unit': price / value,
        'unit': unit,
        'value': value
    }

def add_price_comparisons(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add chain-to-chain price comparisons for products based on item code.
    Enhances product data with price comparison information.
    
    Args:
        products: List of grouped products
        
    Returns:
        Enhanced list of products with price comparisons
    """
    # First, find all products with the same item code that appear in multiple chains
    for product in products:
        # Skip products without prices
        if 'prices' not in product or not product['prices']:
            continue
            
        # Get chains this product appears in
        chains = set()
        chain_prices = {}
        
        for price in product['prices']:
            chain = price.get('chain')
            if chain:
                chains.add(chain)
                # Track lowest price per chain
                if chain not in chain_prices or price['price'] < chain_prices[chain]['price']:
                    chain_prices[chain] = {
                        'price': price['price'],
                        'store_id': price['store_id']
                    }
        
        # If product appears in multiple chains, add comparison
        if len(chains) > 1:
            # Calculate price difference between chains
            comparisons = []
            chains_list = sorted(list(chains))
            
            for i, chain1 in enumerate(chains_list):
                for chain2 in chains_list[i+1:]:
                    price1 = chain_prices[chain1]['price']
                    price2 = chain_prices[chain2]['price']
                    
                    # Calculate absolute and percentage differences
                    diff = price1 - price2
                    if min(price1, price2) > 0:  # Avoid division by zero
                        pct_diff = abs(diff) / min(price1, price2) * 100
                    else:
                        pct_diff = 0
                    
                    # Determine which chain is cheaper
                    cheaper_chain = chain2 if diff > 0 else chain1
                    savings = abs(diff)
                    
                    comparisons.append({
                        'chain1': chain1,
                        'chain2': chain2,
                        'price1': price1,
                        'price2': price2,
                        'difference': diff,
                        'percent_difference': pct_diff,
                        'cheaper_chain': cheaper_chain,
                        'savings': savings
                    })
            
            # Add comparison data to product
            if comparisons:
                product['price_comparisons'] = comparisons
                
                # Add a "best_deal" flag to indicate which chain offers the best price
                min_price = min(p['price'] for p in chain_prices.values())
                for chain, data in chain_prices.items():
                    if data['price'] == min_price:
                        product['best_deal'] = {
                            'chain': chain,
                            'price': min_price,
                            'store_id': data['store_id']
                        }
                        break
    
    return products

def generate_cross_chain_comparison(product):
    """Generate detailed cross-chain price comparison for identical products"""
    print(f"Generating comparison for product: {product.get('item_name', 'Unknown')}")
    
    if 'prices' not in product or len(product['prices']) < 2:
        print(f"Skipping comparison - insufficient prices: {len(product.get('prices', []))}")
        return {}
    
    # Get unique chains and their lowest prices
    chain_prices = {}
    for price in product['prices']:
        chain = price.get('chain')
        if not chain:
            print(f"Skipping price entry with no chain information")
            continue
        
        price_value = price.get('price')
        if price_value is None or price_value <= 0:
            print(f"Skipping invalid price: {price_value} for chain {chain}")
            continue
            
        if chain not in chain_prices or price_value < chain_prices[chain]['price']:
            chain_prices[chain] = {
                'price': price_value,
                'store_id': price.get('store_id', '')
            }
            print(f"Added/Updated price for {chain}: {price_value}")
    
    # Must have at least two chains for comparison
    if len(chain_prices) < 2:
        print(f"Skipping comparison - insufficient chains: {len(chain_prices)}")
        return {}
    
    # Find best and worst deals
    chains = list(chain_prices.keys())
    print(f"Comparing prices across chains: {chains}")
    
    lowest_chain = min(chains, key=lambda c: chain_prices[c]['price'])
    highest_chain = max(chains, key=lambda c: chain_prices[c]['price'])
    
    lowest_price = chain_prices[lowest_chain]['price']
    highest_price = chain_prices[highest_chain]['price']
    
    print(f"Best deal: {lowest_chain} at {lowest_price}")
    print(f"Worst deal: {highest_chain} at {highest_price}")
    
    # Calculate savings
    savings = highest_price - lowest_price
    savings_percent = (savings / highest_price) * 100 if highest_price > 0 else 0
    
    print(f"Savings: {savings} ({savings_percent:.2f}%)")
    
    comparison = {
        'best_deal': {
            'chain': lowest_chain,
            'price': lowest_price,
            'store_id': chain_prices[lowest_chain]['store_id']
        },
        'worst_deal': {
            'chain': highest_chain,
            'price': highest_price,
            'store_id': chain_prices[highest_chain]['store_id']
        },
        'savings': savings,
        'savings_percent': savings_percent,
        'identical_product': True
    }
    
    print(f"Generated comparison data: {comparison}")
    return comparison