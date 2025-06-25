"""
API tests for product endpoints.

Tests the /api/products/* endpoints including search and product details.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database.new_models import Chain, Branch, ChainProduct, BranchPrice


class TestProductEndpoints:
    """Test product-related API endpoints"""

    def test_search_products_success(self, client: TestClient, test_products: dict):
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
        for product in data:
            assert "barcode" in product
            assert "name" in product
            assert "prices_by_store" in product
            assert "price_stats" in product

            # Check price stats
            stats = product["price_stats"]
            assert "min_price" in stats
            assert "max_price" in stats
            assert "avg_price" in stats
            assert "cheapest_store" in stats

    def test_search_products_empty_query(self, client: TestClient):
        """Test searching with empty query"""
        response = client.get(
            "/api/products/search",
            params={"query": "", "city": "תל אביב"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_products_no_results(self, client: TestClient):
        """Test searching for non-existent product"""
        response = client.get(
            "/api/products/search",
            params={"query": "מוצר שלא קיים", "city": "תל אביב"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_search_products_invalid_city(self, client: TestClient):
        """Test searching in non-existent city"""
        response = client.get(
            "/api/products/search",
            params={"query": "חלב", "city": "עיר לא קיימת"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should return empty results for non-existent city
        assert isinstance(data, list)
        assert len(data) == 0

    def test_search_products_limit(self, client: TestClient, test_products: dict):
        """Test search result limit"""
        response = client.get(
            "/api/products/search",
            params={"query": "מוצר", "city": "תל אביב", "limit": 5}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 5

    def test_search_products_invalid_limit(self, client: TestClient):
        """Test search with invalid limit values"""
        # Negative limit
        response = client.get(
            "/api/products/search",
            params={"query": "חלב", "city": "תל אביב", "limit": -1}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Zero limit
        response = client.get(
            "/api/products/search",
            params={"query": "חלב", "city": "תל אביב", "limit": 0}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Too high limit
        response = client.get(
            "/api/products/search",
            params={"query": "חלב", "city": "תל אביב", "limit": 101}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_product_by_barcode_success(self, client: TestClient, test_products: dict):
        """Test getting product details by barcode"""
        barcode = "7290000000001"

        response = client.get(
            f"/api/products/barcode/{barcode}",
            params={"city": "תל אביב"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["barcode"] == barcode
        assert "name" in data
        assert "price_summary" in data
        assert "prices_by_chain" in data
        assert "all_prices" in data

        # Check price summary
        summary = data["price_summary"]
        assert "min_price" in summary
        assert "max_price" in summary
        assert "avg_price" in summary
        assert "savings_potential" in summary

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
        """Test getting product without specifying city"""
        response = client.get("/api/products/barcode/7290000000001")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_available_cities(self, client: TestClient, test_branches: dict):
        """Test getting list of available cities"""
        response = client.get("/api/products/cities")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0
        # Check that test cities are included
        assert "תל אביב" in data
        assert "חיפה" in data

    def test_get_available_chains(self, client: TestClient, test_chains: dict):
        """Test getting list of available chains"""
        response = client.get("/api/products/chains")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Check chain structure
        for chain in data:
            assert "chain_id" in chain
            assert "name" in chain
            assert "display_name" in chain

    def test_get_branches_in_city(self, client: TestClient, test_branches: dict):
        """Test getting branches in a specific city"""
        response = client.get("/api/products/branches/תל אביב")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Check branch structure
        for branch in data:
            assert "branch_id" in branch
            assert "store_id" in branch
            assert "name" in branch
            assert "address" in branch
            assert "chain_name" in branch
            assert branch["city"] == "תל אביב"

    def test_get_branches_with_chain_filter(self, client: TestClient, test_branches: dict, test_chains: dict):
        """Test getting branches filtered by chain"""
        chain_id = test_chains['shufersal'].chain_id

        response = client.get(
            "/api/products/branches/תל אביב",
            params={"chain_id": chain_id}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All branches should be from the specified chain
        for branch in data:
            assert branch["chain_id"] == chain_id

    def test_search_products_hebrew_handling(self, client: TestClient, test_products: dict):
        """Test searching with Hebrew characters and special cases"""
        hebrew_queries = ["חלב", "לחם", "ביצים", "קוטג'"]

        for query in hebrew_queries:
            response = client.get(
                "/api/products/search",
                params={"query": query, "city": "תל אביב"}
            )

            assert response.status_code == status.HTTP_200_OK

    def test_search_products_partial_match(self, client: TestClient, test_products: dict):
        """Test that partial product name matches work"""
        # Search for partial name
        response = client.get(
            "/api/products/search",
            params={"query": "חל", "city": "תל אביב"}  # Partial of חלב
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should find products containing the partial match
        if len(data) > 0:
            assert any("חל" in product["name"] for product in data)

    def test_product_price_consistency(self, client: TestClient, test_products: dict):
        """Test that product prices are consistent across endpoints"""
        barcode = "7290000000001"
        city = "תל אביב"

        # Get from search
        search_response = client.get(
            "/api/products/search",
            params={"query": barcode, "city": city}
        )
        search_data = search_response.json()

        # Get from barcode endpoint
        barcode_response = client.get(
            f"/api/products/barcode/{barcode}",
            params={"city": city}
        )
        barcode_data = barcode_response.json()

        # If found in search, prices should match
        if len(search_data) > 0:
            search_product = next(p for p in search_data if p["barcode"] == barcode)
            assert search_product["price_stats"]["min_price"] == barcode_data["price_summary"]["min_price"]
