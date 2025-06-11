"""
Test script to verify the search engine functionality.
"""
import sys
import os
from pprint import pprint

# Make sure we can import the search engine module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test the search engine
try:
    print("Importing search engine module...")
    from search_engine import search_products, parse_query
    
    # Test parse_query function
    print("\nTesting query parser:")
    test_queries = [
        "במבה",
        "חלב תנובה 3%",
        "דוב",
        "במבה נוגט",
        "שוקולד פרה 100 גרם",
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        parsed = parse_query(query)
        for key, value in parsed.items():
            if value:
                print(f"  - {key}: {value}")
    
    # Test search_products function
    print("\nTesting search products:")
    test_cities = ["Tel Aviv", "Netanya"]
    test_items = ["דוב", "במבה", "חלב"]
    
    for city in test_cities:
        for item in test_items:
            print(f"\nSearching for '{item}' in {city}...")
            try:
                results = search_products(item, city)
                print(f"Found {len(results)} results")
                if results:
                    print("First 3 results:")
                    for i, result in enumerate(results[:3]):
                        print(f"  {i+1}. {result.get('chain')} - {result.get('item_name')} - ₪{result.get('price')}")
            except Exception as e:
                print(f"Error searching: {e}")
    
    print("\n✅ Search engine tests completed!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you have activated the virtual environment and are running from the correct directory.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)