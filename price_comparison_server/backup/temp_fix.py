# Improved version of the balance function
def improved_balance_function(grouped_products, all_results):
    # Convert the grouped products to a list
    grouped_results = list(grouped_products.values())
    
    # Count products by chain
    chain_counts = {}
    for product in grouped_results:
        for price in product.get('prices', []):
            chain = price.get('chain')
            if chain:
                chain_counts[chain] = chain_counts.get(chain, 0) + 1
    
    print(f"Chain distribution before balancing: {chain_counts}")
    
    # Check if both chains are represented
    missing_chains = []
    for expected_chain in ['shufersal', 'victory']:
        if expected_chain not in chain_counts or chain_counts[expected_chain] < 5:
            missing_chains.append(expected_chain)
            
    if missing_chains:
        print(f"Missing or underrepresented chains: {missing_chains}")
        # Try to add products from the missing chains
        for missing_chain in missing_chains:
            # Find products from this chain
            chain_products = [p for p in all_results if p.get('chain') == missing_chain]
            
            if chain_products:
                print(f"Found {len(chain_products)} products from {missing_chain}")
                
                # Sort by name for better organization
                chain_products.sort(key=lambda x: x.get('item_name', ''))
                
                # Add a subset of these products
                for product in chain_products[:20]:
                    product_key = product.get('item_name', '')
                    
                    # Skip if no name
                    if not product_key:
                        continue
                    
                    # Create a new grouped product
                    grouped_result = {
                        "product_name": product_key,
                        "prices": [{
                            "chain": missing_chain,
                            "store_id": product.get('store_id', ''),
                            "price": product.get('item_price', 0),
                            "last_updated": product.get('timestamp', '')
                        }]
                    }
                    
                    # Add to results
                    grouped_results.append(grouped_result)
    
    # Sort by product name for consistent results
    grouped_results.sort(key=lambda x: x.get('product_name', ''))
    
    return grouped_results[:100]  # Limit to 100 results

# Print the function to check it
print(improved_balance_function.__code__)
