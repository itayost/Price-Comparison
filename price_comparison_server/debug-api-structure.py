"""
Quick debug script to check the actual structure of API responses
"""
import requests
import json

API_BASE_URL = "http://localhost:8000"
TEST_CITY = "Tel Aviv"

# Test regular search
print("=== REGULAR SEARCH ===")
response = requests.get(f"{API_BASE_URL}/prices/by-item/{TEST_CITY}/חלב")
if response.status_code == 200:
    results = response.json()
    if results:
        print(f"Total results: {len(results)}")
        print("\nFirst result structure:")
        first = results[0]
        print(json.dumps(first, indent=2, ensure_ascii=False))
        print(f"\nFields in first result: {list(first.keys())}")
        
        # Check if it's a cross-chain product
        if 'prices' in first and isinstance(first['prices'], list):
            print("\nThis is a cross-chain product!")
            print(f"Number of price entries: {len(first['prices'])}")
            if first['prices']:
                print("First price entry:")
                print(json.dumps(first['prices'][0], indent=2, ensure_ascii=False))

# Test grouped search
print("\n\n=== GROUPED SEARCH ===")
response = requests.get(f"{API_BASE_URL}/prices/by-item/{TEST_CITY}/חלב?group_by_code=true")
if response.status_code == 200:
    results = response.json()
    if results:
        print(f"Total results: {len(results)}")
        print("\nFirst result structure:")
        first = results[0]
        print(json.dumps(first, indent=2, ensure_ascii=False))
        print(f"\nFields in first result: {list(first.keys())}")