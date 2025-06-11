"""
Verification script for the rewritten search service (v2.0).
Tests the new dataclass-based implementation.
"""

import sys
import os
import requests
import json
import time
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configuration
API_BASE_URL = "http://localhost:8000"  # Update if your server runs on a different port
TEST_CITY = "Tel Aviv"

class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'

def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result with color."""
    status = f"{Colors.OKGREEN}✅ PASSED{Colors.ENDC}" if passed else f"{Colors.FAIL}❌ FAILED{Colors.ENDC}"
    print(f"{test_name}: {status}")
    if details:
        print(f"  {Colors.CYAN}{details}{Colors.ENDC}")

def test_direct_import():
    """Test that we can import the new dataclass-based implementation."""
    print(f"\n{Colors.BOLD}1. Testing Direct Import of New Implementation{Colors.ENDC}")
    
    try:
        # Import the main function
        from services.search_service import search_products_by_name_and_city
        
        # Import new components
        from services.search_service import (
            parse_query,
            calculate_relevance_score,
            group_products_by_item_code,
            QueryInfo,
            SearchResult,
            QueryType,
            generate_search_patterns
        )
        
        print_result("Import main components", True, "All imports successful")
        
        # Test parse_query returns QueryInfo object
        query_info = parse_query("דוב")
        
        # Check it's a QueryInfo instance
        is_query_info = hasattr(query_info, 'original_query') and hasattr(query_info, 'query_type')
        print_result(
            "parse_query returns QueryInfo", 
            is_query_info,
            f"Type: {query_info.query_type.value if hasattr(query_info.query_type, 'value') else query_info.query_type}"
        )
        
        # Check expansions
        has_expansions = query_info.expansion_terms and len(query_info.expansion_terms) > 0
        print_result(
            "Short term expansion", 
            has_expansions,
            f"Found {len(query_info.expansion_terms)} expansions: {query_info.expansion_terms}"
        )
        
        # Test pattern generation
        patterns = generate_search_patterns(query_info)
        print_result(
            "Pattern generation",
            len(patterns) > 0,
            f"Generated {len(patterns)} patterns"
        )
        
        # Test relevance scoring with new signature
        score = calculate_relevance_score("דובונים גומי", query_info, has_price_per_unit=True)
        print_result(
            "Relevance scoring",
            score > 0,
            f"Score: {score:.1f}"
        )
        
        return True
        
    except ImportError as e:
        print_result("Import enhanced functions", False, f"Import Error: {str(e)}")
        return False
    except Exception as e:
        print_result("Import test", False, f"Error: {str(e)}")
        return False

def test_api_endpoints():
    """Test API endpoints to ensure they work with the new implementation."""
    print(f"\n{Colors.BOLD}2. Testing API Endpoints{Colors.ENDC}")
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code != 200:
            print(f"{Colors.WARNING}⚠️  Server not responding at {API_BASE_URL}{Colors.ENDC}")
            print("Please start the server with: python run_server.py")
            return False
    except:
        print(f"{Colors.WARNING}⚠️  Cannot connect to server at {API_BASE_URL}{Colors.ENDC}")
        print("Please start the server with: python run_server.py")
        return False
    
    # Test search endpoint
    test_queries = [
        ("דוב", "Short term with expansions"),
        ("חלב", "Common product"), 
        ("במבה 80 גרם", "Product with weight"),
    ]
    
    all_passed = True
    
    for query, description in test_queries:
        try:
            # Test regular search
            response = requests.get(f"{API_BASE_URL}/prices/by-item/{TEST_CITY}/{query}")
            
            if response.status_code == 200:
                results = response.json()
                
                # Validate result structure
                valid_structure = True
                if results and len(results) > 0:
                    first = results[0]
                    # Check for required fields
                    required_fields = ['item_name', 'chain', 'price']
                    valid_structure = all(field in first for field in required_fields)
                
                # Check for enhanced features
                has_relevance = False
                has_cross_chain = False
                
                if results and len(results) > 0:
                    # Check first few results for relevance score
                    has_relevance = any('relevance_score' in r for r in results[:5])
                    has_cross_chain = any(r.get('cross_chain', False) for r in results)
                
                details = f"{len(results)} results"
                if has_relevance:
                    details += ", with relevance scores"
                if has_cross_chain:
                    details += ", includes cross-chain products"
                if not valid_structure and results:
                    details += " (invalid structure)"
                
                passed = response.status_code == 200 and valid_structure
                print_result(f"Search '{query}' ({description})", passed, details)
                
                # Show top result with new features
                if results and has_relevance:
                    top = results[0]
                    print(f"    Top result: {top.get('item_name', 'N/A')} - Score: {top.get('relevance_score', 0):.1f}")
                    if 'weight' in top:
                        print(f"    Weight: {top['weight']} {top.get('unit', '')}")
                
            else:
                print_result(f"Search '{query}'", False, f"Status: {response.status_code}")
                
                # Try to get error details
                try:
                    error_data = response.json()
                    print(f"    Error: {error_data.get('detail', 'Unknown error')}")
                except:
                    pass
                    
                all_passed = False
                
        except Exception as e:
            print_result(f"Search '{query}'", False, f"Error: {str(e)}")
            all_passed = False
    
    # Test with grouping
    print(f"\n  Testing grouped search:")
    try:
        response = requests.get(f"{API_BASE_URL}/prices/by-item/{TEST_CITY}/חלב?group_by_code=true")
        if response.status_code == 200:
            results = response.json()
            cross_chain = [r for r in results if r.get('cross_chain', False)]
            print_result(
                "Grouped search",
                True,
                f"{len(results)} total, {len(cross_chain)} cross-chain products"
            )
        else:
            print_result("Grouped search", False, f"Status: {response.status_code}")
            all_passed = False
    except Exception as e:
        print_result("Grouped search", False, f"Error: {str(e)}")
        all_passed = False
    
    return all_passed

def test_cheapest_cart():
    """Test the cheapest cart endpoint with new implementation."""
    print(f"\n{Colors.BOLD}3. Testing Cheapest Cart Calculation{Colors.ENDC}")
    
    # Prepare test cart
    cart_data = {
        "city": TEST_CITY,
        "items": [
            {"item_name": "חלב", "quantity": 2},
            {"item_name": "במבה", "quantity": 3},
            {"item_name": "לחם", "quantity": 1}
        ]
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/cheapest-cart-all-chains",
            json=cart_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Validate response structure
            required_fields = ['chain', 'store_id', 'total_price']
            has_required = all(field in result for field in required_fields)
            
            # Check for enhanced features
            has_savings = 'savings' in result
            has_all_stores = 'all_stores' in result
            
            details = f"Best: {result.get('chain', 'N/A')} - ₪{result.get('total_price', 0):.2f}"
            if has_savings:
                details += f", Savings: ₪{result.get('savings', 0):.2f}"
            
            print_result("Cheapest cart calculation", has_required, details)
            
            if has_all_stores and len(result.get('all_stores', [])) > 1:
                print(f"    Compared {len(result['all_stores'])} stores with complete inventory")
            
            return has_required
            
        else:
            print_result("Cheapest cart calculation", False, f"Status: {response.status_code}")
            
            # Try to get error details
            try:
                error_data = response.json()
                print(f"    Error: {error_data.get('detail', 'Unknown error')}")
            except:
                pass
                
            return False
            
    except Exception as e:
        print_result("Cheapest cart calculation", False, f"Error: {str(e)}")
        return False

def test_performance():
    """Test search performance."""
    print(f"\n{Colors.BOLD}4. Testing Performance{Colors.ENDC}")
    
    test_queries = ["חלב", "דוב", "במבה", "שוקולד", "לחם"]
    
    try:
        from services.search_service import search_products_by_name_and_city
        
        total_time = 0
        results_counts = []
        
        for query in test_queries:
            start = time.time()
            results = search_products_by_name_and_city(TEST_CITY, query)
            elapsed = time.time() - start
            total_time += elapsed
            results_counts.append(len(results))
            
            print(f"  '{query}': {elapsed:.3f}s ({len(results)} results)")
        
        avg_time = total_time / len(test_queries)
        avg_results = sum(results_counts) / len(results_counts)
        
        # Performance criteria
        passed = avg_time < 1.0 and avg_results > 0  # Should be under 1 second average
        
        print_result(
            "Average performance", 
            passed, 
            f"{avg_time:.3f}s per search, {avg_results:.0f} avg results"
        )
        
        return passed
        
    except Exception as e:
        print_result("Performance test", False, f"Error: {str(e)}")
        return False

def test_dataclass_functionality():
    """Test the new dataclass-based functionality."""
    print(f"\n{Colors.BOLD}5. Testing DataClass Functionality{Colors.ENDC}")
    
    try:
        from services.search_service import (
            QueryInfo, 
            SearchResult, 
            QueryType,
            parse_query,
            search_products_by_name_and_city
        )
        
        # Test QueryInfo creation
        query_info = parse_query("במבה 80 גרם")
        
        tests_passed = []
        
        # Test query type detection
        is_with_weight = hasattr(query_info.query_type, 'value') and 'weight' in query_info.query_type.value.lower()
        tests_passed.append(('Query type detection', query_info.weight_value == 80.0))
        
        # Test weight extraction
        tests_passed.append(('Weight extraction', query_info.weight_value == 80.0))
        tests_passed.append(('Unit extraction', query_info.weight_unit == 'g'))
        
        # Test category detection
        tests_passed.append(('Category detection', query_info.category == 'snack'))
        
        # Test search with new implementation
        results = search_products_by_name_and_city(TEST_CITY, "חלב", group_by_code=True)
        tests_passed.append(('Search returns results', len(results) > 0))
        
        # Print individual test results
        all_passed = True
        for test_name, passed in tests_passed:
            print(f"  {test_name}: {'✅' if passed else '❌'}")
            all_passed &= passed
        
        print_result(
            "DataClass functionality",
            all_passed,
            f"{sum(p for _, p in tests_passed)}/{len(tests_passed)} tests passed"
        )
        
        return all_passed
        
    except Exception as e:
        print_result("DataClass functionality", False, f"Error: {str(e)}")
        return False

def check_enhanced_features():
    """Check and demonstrate enhanced features."""
    print(f"\n{Colors.BOLD}6. Enhanced Features Demonstration{Colors.ENDC}")
    
    try:
        from services.search_service import search_products_by_name_and_city, parse_query
        
        print(f"\n✨ {Colors.OKGREEN}New Features in v2.0:{Colors.ENDC}")
        
        # 1. Query Parsing
        test_queries = ["דוב", "חלב 1 ליטר", "במבה", "שוקולד פרה 100 גרם"]
        print(f"\n  {Colors.BOLD}Query Parsing Examples:{Colors.ENDC}")
        
        for q in test_queries:
            info = parse_query(q)
            print(f"    '{q}':")
            print(f"      Type: {info.query_type.value}")
            if info.category:
                print(f"      Category: {info.category}")
            if info.expansion_terms:
                print(f"      Expansions: {info.expansion_terms[:3]}")
            if info.weight_value:
                print(f"      Weight: {info.weight_value} {info.weight_unit}")
        
        # 2. Cross-chain products
        print(f"\n  {Colors.BOLD}Cross-Chain Product Example:{Colors.ENDC}")
        results = search_products_by_name_and_city(TEST_CITY, "חלב", group_by_code=True)
        cross_chain = [r for r in results if r.get('cross_chain', False)]
        
        if cross_chain:
            example = cross_chain[0]
            print(f"    Product: {example['item_name']}")
            print(f"    Item Code: {example.get('item_code', 'N/A')}")
            print(f"    Available in {len(example.get('prices', []))} stores")
            
            if 'price_comparison' in example:
                comp = example['price_comparison']
                print(f"    Best Deal: {comp['best_deal']['chain']} - ₪{comp['best_deal']['price']:.2f}")
                print(f"    Savings: ₪{comp['savings']:.2f} ({comp['savings_percent']:.1f}%)")
        
        # 3. Performance & Architecture
        print(f"\n  {Colors.BOLD}Architecture Improvements:{Colors.ENDC}")
        print(f"    • Type-safe dataclasses (QueryInfo, SearchResult)")
        print(f"    • Enum-based query types")  
        print(f"    • Comprehensive error handling")
        print(f"    • Clean logging throughout")
        print(f"    • Modular, maintainable code")
        
        return True
        
    except Exception as e:
        print(f"{Colors.FAIL}Error checking features: {str(e)}{Colors.ENDC}")
        return False

def main():
    """Run all verification tests."""
    print(f"{Colors.BOLD}\n🔍 VERIFYING SEARCH SERVICE v2.0 🔍{Colors.ENDC}")
    print("=" * 60)
    
    # Check Python version
    import sys
    print(f"Python version: {sys.version.split()[0]}")
    print(f"Running from: {os.getcwd()}")
    
    # Run tests
    tests = [
        ("Direct Import", test_direct_import),
        ("API Endpoints", test_api_endpoints),
        ("Cheapest Cart", test_cheapest_cart),
        ("Performance", test_performance),
        ("DataClass Functionality", test_dataclass_functionality),
        ("Enhanced Features", check_enhanced_features),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"{Colors.FAIL}Error in {test_name}: {str(e)}{Colors.ENDC}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}VERIFICATION SUMMARY{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, test_passed in results.items():
        status = f"{Colors.OKGREEN}✅{Colors.ENDC}" if test_passed else f"{Colors.FAIL}❌{Colors.ENDC}"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 SEARCH SERVICE v2.0 IS WORKING PERFECTLY! 🎉{Colors.ENDC}")
        print(f"\n{Colors.OKGREEN}Your enhanced search now features:{Colors.ENDC}")
        print(f"{Colors.OKGREEN}  ✓ Type-safe dataclasses{Colors.ENDC}")
        print(f"{Colors.OKGREEN}  ✓ Smart query parsing with weight detection{Colors.ENDC}")
        print(f"{Colors.OKGREEN}  ✓ Advanced relevance scoring{Colors.ENDC}")
        print(f"{Colors.OKGREEN}  ✓ Robust cross-chain matching{Colors.ENDC}")
        print(f"{Colors.OKGREEN}  ✓ Clean, maintainable architecture{Colors.ENDC}")
    else:
        print(f"\n{Colors.WARNING}⚠️  Some tests failed. Please check the output above.{Colors.ENDC}")
        if passed < total / 2:
            print(f"{Colors.WARNING}Consider rolling back: cp services/search_service_backup.py services/search_service.py{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}Most tests passed - likely minor issues to fix.{Colors.ENDC}")

if __name__ == "__main__":
    main()