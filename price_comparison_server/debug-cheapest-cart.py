#!/usr/bin/env python3
"""
Debug script to test cheapest cart and see the actual error
"""
import sys
import json

try:
    import requests
except ImportError:
    print("Error: requests module not found!")
    print("Please install it with: pip install requests")
    sys.exit(1)

API_BASE_URL = "http://localhost:8000"
TEST_CITY = "Tel Aviv"

# Test cheapest cart
cart_data = {
    "city": TEST_CITY,
    "items": [
        {"item_name": "חלב", "quantity": 2},
        {"item_name": "במבה", "quantity": 3}
    ]
}

print("=== TESTING CHEAPEST CART ===")
print("Request data:")
print(json.dumps(cart_data, indent=2, ensure_ascii=False))

try:
    response = requests.post(
        f"{API_BASE_URL}/cheapest-cart-all-chains",
        json=cart_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    # Try to get the response content
    try:
        data = response.json()
        print("\nResponse JSON:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print("\nRaw Response:")
        print(response.text)
        
except Exception as e:
    print(f"\nRequest failed with error: {e}")

# Also test with a simpler cart
print("\n\n=== TESTING WITH SINGLE ITEM ===")
simple_cart = {
    "city": TEST_CITY,
    "items": [
        {"item_name": "חלב", "quantity": 1}
    ]
}

try:
    response = requests.post(
        f"{API_BASE_URL}/cheapest-cart-all-chains",
        json=simple_cart,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Success! Single item cart works")
    else:
        try:
            print(f"Error: {response.json()}")
        except:
            print(f"Error: {response.text}")
            
except Exception as e:
    print(f"Request failed: {e}")