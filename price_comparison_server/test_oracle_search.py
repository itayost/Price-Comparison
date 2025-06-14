#!/usr/bin/env python3
"""
Test API endpoints with the new Oracle-compatible search
"""

import requests
import json
import time
from typing import Dict, Any, List

# API Configuration
# Update this with your Railway URL
API_BASE_URL = "https://price-comparison-production-3906.up.railway.app/"  # Replace with your actual Railway URL
TEST_CITY = "Tel Aviv"

# You can also use environment variable
import os
API_BASE_URL = os.getenv("RAILWAY_API_URL", "https://price-comparison-production-3906.up.railway.app/")

# ANSI color codes for output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_test_header(test_name: str):
    """Print a formatted test header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{test_name}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")

def print_result(success: bool, message: str):
    """Print a colored result message"""
    if success:
        print(f"{Colors.GREEN}✅ {message}{Colors.END}")
    else:
        print(f"{Colors.RED}❌ {message}{Colors.END}")

def test_health_check():
    """Test the health check endpoint"""
    print_test_header("HEALTH CHECK")

    try:
        response = requests.get(f"{API_BASE_URL}/health")
        data = response.json()

        print_result(response.status_code == 200, f"Health check status: {response.status_code}")
        print(f"  Database: {data.get('database', 'Unknown')}")
        print(f"  Database Type: {data.get('database_type', 'Unknown')}")
        print(f"  Has Stores: {data.get('has_stores', False)}")
        print(f"  Has Prices: {data.get('has_prices', False)}")

        return response.status_code == 200
    except Exception as e:
        print_result(False, f"Health check failed: {str(e)}")
        return False

def test_cities_endpoints():
    """Test city-related endpoints"""
    print_test_header("CITIES ENDPOINTS")

    success = True

    # Test simple cities list
    try:
        response = requests.get(f"{API_BASE_URL}/cities-list")
        cities = response.json()

        print_result(response.status_code == 200, f"Cities list: {len(cities)} cities found")
        if cities:
            print(f"  Sample cities: {', '.join(cities[:5])}")
    except Exception as e:
        print_result(False, f"Cities list failed: {str(e)}")
        success = False

    # Test cities with stores
    try:
        response = requests.get(f"{API_BASE_URL}/cities-list-with-stores")
        cities_with_stores = response.json()

        print_result(response.status_code == 200, f"Cities with stores: {len(cities_with_stores)} entries")
        if cities_with_stores:
            print(f"  Sample: {cities_with_stores[0]}")
    except Exception as e:
        print_result(False, f"Cities with stores failed: {str(e)}")
        success = False

    return success

def test_product_search():
    """Test product search endpoints"""
    print_test_header("PRODUCT SEARCH")

    test_searches = [
        ("חלב", "Basic search"),
        ("במבה", "Popular snack"),
        ("שוקולד פרה 100 גרם", "Search with weight"),
        ("דוב", "Short term search"),
    ]

    success = True

    for query, description in test_searches:
        print(f"\n{Colors.BOLD}Test: {description}{Colors.END}")
        print(f"Query: '{query}'")

        try:
            # Test regular search
            start_time = time.time()
            response = requests.get(f"{API_BASE_URL}/prices/by-item/{TEST_CITY}/{query}")
            elapsed = time.time() - start_time

            if response.status_code == 200:
                results = response.json()
                print_result(True, f"Found {len(results)} results in {elapsed:.3f}s")

                if results:
                    first = results[0]
                    print(f"  First result: {first.get('item_name', 'Unknown')}")
                    print(f"  Price: ₪{first.get('price', 0)}")

                    # Check for cross-chain products
                    cross_chain = [r for r in results if r.get('cross_chain', False)]
                    if cross_chain:
                        print(f"  Cross-chain products: {len(cross_chain)}")
            else:
                print_result(False, f"Search failed with status {response.status_code}")
                success = False

        except Exception as e:
            print_result(False, f"Search error: {str(e)}")
            success = False

    return success

def test_identical_products():
    """Test identical products endpoint"""
    print_test_header("IDENTICAL PRODUCTS")

    try:
        response = requests.get(f"{API_BASE_URL}/prices/identical-products/{TEST_CITY}/חלב")

        if response.status_code == 200:
            products = response.json()
            print_result(True, f"Found {len(products)} identical products")

            if products:
                first = products[0]
                print(f"\nExample identical product:")
                print(f"  Name: {first.get('item_name', 'Unknown')}")
                print(f"  Item Code: {first.get('item_code', 'Unknown')}")

                if 'price_comparison' in first:
                    comp = first['price_comparison']
                    print(f"  Best Deal: {comp['best_deal']['chain']} - ₪{comp['best_deal']['price']}")
                    print(f"  Savings: ₪{comp['savings']:.2f} ({comp['savings_percent']:.1f}%)")

            return True
        else:
            print_result(False, f"Request failed with status {response.status_code}")
            return False

    except Exception as e:
        print_result(False, f"Identical products error: {str(e)}")
        return False

def test_cheapest_cart():
    """Test cheapest cart calculation"""
    print_test_header("CHEAPEST CART CALCULATION")

    cart_data = {
        "city": TEST_CITY,
        "items": [
            {"item_name": "חלב", "quantity": 2},
            {"item_name": "לחם", "quantity": 1},
            {"item_name": "ביצים", "quantity": 1}
        ]
    }

    try:
        print("Cart items:")
        for item in cart_data['items']:
            print(f"  - {item['item_name']} x {item['quantity']}")

        response = requests.post(
            f"{API_BASE_URL}/cheapest-cart-all-chains",
            json=cart_data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            result = response.json()
            print_result(True, "Cheapest cart calculated successfully")

            print(f"\nBest Store:")
            print(f"  Chain: {result.get('chain', 'Unknown')}")
            print(f"  Store ID: {result.get('store_id', 'Unknown')}")
            print(f"  Total Price: ₪{result.get('total_price', 0):.2f}")

            if 'savings' in result:
                print(f"\nSavings:")
                print(f"  Amount: ₪{result['savings']:.2f}")
                print(f"  Percentage: {result['savings_percent']:.1f}%")

            if 'all_stores' in result and len(result['all_stores']) > 1:
                print(f"\nCompared {len(result['all_stores'])} stores with all items")

            return True
        else:
            print_result(False, f"Request failed with status {response.status_code}")
            if response.text:
                print(f"  Error: {response.text}")
            return False

    except Exception as e:
        print_result(False, f"Cheapest cart error: {str(e)}")
        return False

def test_statistics():
    """Test statistics endpoint"""
    print_test_header("DATABASE STATISTICS")

    try:
        response = requests.get(f"{API_BASE_URL}/statistics/overview")

        if response.status_code == 200:
            stats = response.json()
            print_result(True, "Statistics retrieved successfully")

            print(f"\nDatabase Overview:")
            print(f"  Total Stores: {stats.get('total_stores', 0)}")
            print(f"  Total Prices: {stats.get('total_prices', 0)}")
            print(f"  Total Cities: {stats.get('total_cities', 0)}")

            if 'chains' in stats:
                print(f"\nBy Chain:")
                for chain, data in stats['chains'].items():
                    print(f"  {chain}: {data['stores']} stores, {data['prices']} prices")

            return True
        else:
            print_result(False, f"Request failed with status {response.status_code}")
            return False

    except Exception as e:
        print_result(False, f"Statistics error: {str(e)}")
        return False

def test_performance():
    """Test API performance with multiple queries"""
    print_test_header("PERFORMANCE TEST")

    queries = ['חלב', 'במבה', 'שוקולד', 'לחם', 'ביצים']
    total_time = 0
    success_count = 0

    print("Running multiple search queries...")

    for query in queries:
        try:
            start_time = time.time()
            response = requests.get(f"{API_BASE_URL}/prices/by-item/{TEST_CITY}/{query}")
            elapsed = time.time() - start_time
            total_time += elapsed

            if response.status_code == 200:
                results = response.json()
                print(f"  '{query}': {elapsed:.3f}s ({len(results)} results)")
                success_count += 1
            else:
                print(f"  '{query}': Failed with status {response.status_code}")

        except Exception as e:
            print(f"  '{query}': Error - {str(e)}")

    if success_count > 0:
        avg_time = total_time / success_count
        print(f"\nAverage response time: {avg_time:.3f}s")

        if avg_time < 0.5:
            print_result(True, "Performance is excellent!")
        elif avg_time < 1.0:
            print_result(True, "Performance is good")
        else:
            print_result(False, "Performance needs optimization")

    return success_count == len(queries)

def main():
    """Run all API tests"""
    print(f"{Colors.BOLD}{Colors.GREEN}")
    print("🔍 ORACLE API ENDPOINT TESTS 🔍")
    print(f"API URL: {API_BASE_URL}")
    print(f"Test City: {TEST_CITY}")
    print(f"{Colors.END}")

    # First check if server is running
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print_result(False, "Server is not responding properly")
            print("Please make sure the server is running:")
            print("  cd price_comparison_server")
            print("  python run_server.py")
            return
    except requests.exceptions.ConnectionError:
        print_result(False, "Cannot connect to server")
        print("Please start the server first:")
        print("  cd price_comparison_server")
        print("  python run_server.py")
        return
    except Exception as e:
        print_result(False, f"Server check failed: {str(e)}")
        return

    # Run all tests
    tests = [
        ("Health Check", test_health_check),
        ("Cities Endpoints", test_cities_endpoints),
        ("Product Search", test_product_search),
        ("Identical Products", test_identical_products),
        ("Cheapest Cart", test_cheapest_cart),
        ("Statistics", test_statistics),
        ("Performance", test_performance),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print_result(False, f"{test_name} crashed: {str(e)}")
            results[test_name] = False

    # Summary
    print_test_header("TEST SUMMARY")

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    print(f"\nResults: {passed}/{total} tests passed")

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status}{Colors.END} - {test_name}")

    if passed == total:
        print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 ALL TESTS PASSED! 🎉{Colors.END}")
        print("\nThe Oracle integration is working perfectly!")
        print("Next steps:")
        print("1. Run full scraping for both chains")
        print("2. Monitor performance in production")
        print("3. Set up regular scraping schedule")
    else:
        print(f"\n{Colors.YELLOW}⚠️  Some tests failed. Please check the logs above.{Colors.END}")

if __name__ == "__main__":
    main()
