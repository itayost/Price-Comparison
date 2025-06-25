"""
API tests for product search endpoints.

Tests the /api/products/* endpoints including search and product details.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import List, Dict

from database.new_models import Chain, Branch, ChainProduct, BranchPrice


class TestProductEndpoints:
    """Test product-related API endpoints"""
    
    def test_search_products_success(self, client: TestClient, test_prices: dict):
        """Test successful product search"""
        response = client.get(
            "/api/products/search",
            params={"query": "חלב", "city": "תל אביב", "limit": 10}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check product structure
        product = data[0]
        assert "barcode" in product
        assert "name" in product
        assert "prices_by_store" in product
        assert "price_stats" in product
        
        # Check price statistics
        stats = product["price_stats"]
        assert "min_price" in stats
        assert "max_price" in stats
        assert "avg_price" in stats
        assert "cheapest_store" in stats
        
        # Check that search term is in results
        assert any("חלב" in p["name"] for p in data)
    
    def test_search_products_empty_results(self, client: TestClient):
        """Test search with no results"""
        response = client.get(
            "/api/products/search",
            params={"query": "מוצר לא קיים", "city": "תל אביב"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_search_products_missing_params(self, client: TestClient):
        """Test search with missing required parameters"""
        # Missing city
        response = client.get(
            "/api/products/search",
            params={"query": "חלב"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing query
        response = client.get(
            "/api/products/search",
            params={"city": "תל אביב"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_search_products_limit(self, client: TestClient, test_prices: dict):
        """Test search limit parameter"""
        # Test with limit
        response = client.get(
            "/api/products/search",
            params={"query": "מוצר", "city": "תל אביב", "limit": 5}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 5
        
        # Test with invalid limit
        response = client.get(
            "/api/products/search",
            params={"query": "מוצר", "city": "תל אביב", "limit": 0}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        response = client.get(
            "/api/products/search",
            params={"query": "מוצר", "city": "תל אביב", "limit": 101}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_product_by_barcode_success(self, client: TestClient, test_prices: dict):
        """Test getting product by barcode"""
        barcode = "7290000000001"
        
        response = client.get(
            f"/api/products/barcode/{barcode}",
            params={"city": "תל אביב"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["barcode"] == barcode
        assert "name" in data
        assert "available" in data
        assert data["available"] is True
        
        # Check price summary
        assert "price_summary" in data
        summary = data["price_summary"]
        assert "min_price" in summary
        assert "max_price" in summary
        assert "avg_price" in summary
        assert "total_stores" in summary
        assert "savings_potential" in summary
        
        # Check prices by chain
        assert "prices_by_chain" in data
        assert len(data["prices_by_chain"]) > 0
        
        # Check all prices
        assert "all_prices" in data
        assert len(data["all_prices"]) > 0
        
        # Verify prices are sorted
        prices = [p["price"] for p in data["all_prices"]]
        assert prices == sorted(prices)
    
    def test_get_product_by_barcode_not_found(self, client: TestClient):
        """Test getting non-existent product by barcode"""
        response = client.get(
            "/api/products/barcode/9999999999999",
            params={"city": "תל אביב"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_get_product_by_barcode_missing_city(self, client: TestClient):
        """Test getting product without city parameter"""
        response = client.get("/api/products/barcode/7290000000001")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_available_cities(self, client: TestClient, test_branches: dict):
        """Test getting list of available cities"""
        response = client.get("/api/products/cities")
        
        assert response.status_code == status.HTTP_200_OK
        cities = response.json()
        
        assert isinstance(cities, list)
        assert len(cities) > 0
        assert "תל אביב" in cities
        
        # Cities should be sorted
        assert cities == sorted(cities)
    
    def test_get_available_chains(self, client: TestClient, test_chains: dict):
        """Test getting list of available chains"""
        response = client.get("/api/products/chains")
        
        assert response.status_code == status.HTTP_200_OK
        chains = response.json()
        
        assert isinstance(chains, list)
        assert len(chains) > 0
        
        # Check chain structure
        for chain in chains:
            assert "chain_id" in chain
            assert "name" in chain
            assert "display_name" in chain
        
        # Verify our test chains are included
        chain_names = [c["name"] for c in chains]
        assert "shufersal" in chain_names
        assert "victory" in chain_names
    
    def test_get_branches_in_city(self, client: TestClient, test_branches: dict):
        """Test getting branches in a specific city"""
        response = client.get("/api/products/branches/תל אביב")
        
        assert response.status_code == status.HTTP_200_OK
        branches = response.json()
        
        assert isinstance(branches, list)
        assert len(branches) > 0
        
        # Check branch structure
        for branch in branches:
            assert "branch_id" in branch
            assert "store_id" in branch
            assert "name" in branch
            assert "address" in branch
            assert "city" in branch
            assert "chain_name" in branch
            assert "chain_display_name" in branch
            
            # All should be in Tel Aviv
            assert branch["city"] == "תל אביב"
    
    def test_get_branches_with_chain_filter(self, client: TestClient, test_branches: dict, test_chains: dict):
        """Test getting branches filtered by chain"""
        shufersal_chain_id = test_chains["shufersal"].chain_id
        
        response = client.get(
            "/api/products/branches/תל אביב",
            params={"chain_id": shufersal_chain_id}
        )
        
        assert response.status_code == status.HTTP_200_OK
        branches = response.json()
        
        # All branches should be from Shufersal
        for branch in branches:
            assert branch["chain_name"] == "shufersal"
    
    def test_search_products_hebrew_normalization(self, client: TestClient, test_prices: dict):
        """Test that Hebrew search handles different spellings"""
        # Different ways to search for cottage cheese
        queries = ["קוטג", "קוטג'", "גבינת קוטג"]
        
        for query in queries:
            response = client.get(
                "/api/products/search",
                params={"query": query, "city": "תל אביב"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            # Should find results for all variations
    
    def test_search_products_partial_match(self, client: TestClient, test_prices: dict):
        """Test partial product name matching"""
        response = client.get(
            "/api/products/search",
            params={"query": "חל", "city": "תל אביב"}  # Partial of חלב
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should find products containing the partial match
        if len(data) > 0:
            assert any("חל" in p["name"] for p in data)
    
    def test_product_price_consistency(self, client: TestClient, test_prices: dict):
        """Test that product prices are consistent across endpoints"""
        barcode = "7290000000001"
        city = "תל אביב"
        
        # Get from search
        search_response = client.get(
            "/api/products/search",
            params={"query": "חלב", "city": city}
        )
        search_data = search_response.json()
        
        # Get from barcode endpoint
        barcode_response = client.get(
            f"/api/products/barcode/{barcode}",
            params={"city": city}
        )
        barcode_data = barcode_response.json()
        
        # Find the same product in search results
        search_product = next(
            (p for p in search_data if p["barcode"] == barcode),
            None
        )
        
        if search_product:
            # Prices should be consistent
            assert search_product["price_stats"]["min_price"] == barcode_data["price_summary"]["min_price"]
            assert search_product["price_stats"]["max_price"] == barcode_data["price_summary"]["max_price"]
    
    def test_search_products_case_insensitive(self, client: TestClient, test_prices: dict):
        """Test that search is case-insensitive for English"""
        queries = ["MILK", "milk", "Milk"]
        
        results = []
        for query in queries:
            response = client.get(
                "/api/products/search",
                params={"query": query, "city": "תל אביב"}
            )
            assert response.status_code == status.HTTP_200_OK
            results.append(len(response.json()))
        
        # All queries should return the same number of results
        # (or at least all should be consistent - all 0 or all > 0)
        assert len(set(results)) <= 1
