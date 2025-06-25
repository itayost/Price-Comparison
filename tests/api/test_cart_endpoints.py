"""
API tests for cart comparison endpoints.

Tests the /api/cart/* endpoints including cart comparison and product search.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, Mock

from database.new_models import User, SavedCart
from tests.fixtures.sample_products import SAMPLE_CART_ITEMS


class TestCartEndpoints:
    """Test cart-related API endpoints"""

    def test_compare_cart_success(self, client: TestClient, test_prices: dict):
        """Test successful cart comparison"""
        cart_data = {
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 2},
                {"barcode": "7290000000002", "quantity": 1}
            ]
        }

        response = client.post("/api/cart/compare", json=cart_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "total_items" in data
        assert data["total_items"] == 2
        assert "cheapest_store" in data
        assert "all_stores" in data
        assert len(data["all_stores"]) > 0

        # Check cheapest store structure
        if data["cheapest_store"]:
            cheapest = data["cheapest_store"]
            assert "chain_name" in cheapest
            assert "branch_name" in cheapest
            assert "total_price" in cheapest
            assert "available_items" in cheapest
            assert "missing_items" in cheapest

    def test_compare_cart_empty_items(self, client: TestClient):
        """Test cart comparison with empty items list"""
        cart_data = {
            "city": "תל אביב",
            "items": []
        }

        response = client.post("/api/cart/compare", json=cart_data)

        # Should return bad request or handle gracefully
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["success"] is False

    def test_compare_cart_invalid_city(self, client: TestClient):
        """Test cart comparison with non-existent city"""
        cart_data = {
            "city": "עיר לא קיימת",
            "items": [{"barcode": "7290000000001", "quantity": 1}]
        }

        response = client.post("/api/cart/compare", json=cart_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should succeed but with no stores found
        assert data["cheapest_store"] is None or len(data["all_stores"]) == 0

    def test_compare_cart_invalid_barcode(self, client: TestClient, test_branches: dict):
        """Test cart comparison with invalid barcode"""
        cart_data = {
            "city": "תל אביב",
            "items": [
                {"barcode": "9999999999999", "quantity": 1}
            ]
        }

        response = client.post("/api/cart/compare", json=cart_data)

        # Should still work but product won't be found
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if data["cheapest_store"]:
            assert data["cheapest_store"]["missing_items"] >= 1 or data["cheapest_store"]["available_items"] == 0

    def test_compare_cart_missing_fields(self, client: TestClient):
        """Test cart comparison with missing required fields"""
        # Missing city
        response = client.post("/api/cart/compare", json={"items": []})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing items
        response = client.post("/api/cart/compare", json={"city": "תל אביב"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_compare_cart_negative_quantity(self, client: TestClient):
        """Test cart comparison with negative quantity"""
        cart_data = {
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": -1}
            ]
        }

        response = client.post("/api/cart/compare", json=cart_data)

        # Should reject negative quantities
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST]

    def test_compare_cart_multiple_items(self, client: TestClient, test_prices: dict):
        """Test comparing cart with multiple items"""
        cart_data = {
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 2, "name": "חלב"},
                {"barcode": "7290000000002", "quantity": 1, "name": "לחם"},
                {"barcode": "7290000000003", "quantity": 3, "name": "ביצים"}
            ]
        }

        response = client.post("/api/cart/compare", json=cart_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["total_items"] == 3

        # Check that all stores are calculated
        for store in data["all_stores"]:
            assert store["total_price"] > 0
            assert store["available_items"] >= 0
            assert store["available_items"] + store["missing_items"] == 3

    def test_get_product_info(self, client: TestClient, test_products: dict):
        """Test getting product information by barcode"""
        barcode = "7290000000001"

        response = client.get(f"/api/cart/product/{barcode}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "product" in data
        product = data["product"]
        assert product["barcode"] == barcode
        assert "name" in product
        assert "prices" in product

    def test_get_nonexistent_product(self, client: TestClient):
        """Test getting non-existent product"""
        response = client.get("/api/cart/product/9999999999999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_search_products(self, client: TestClient, test_products: dict):
        """Test searching products"""
        response = client.get("/api/cart/search", params={"query": "חלב", "limit": 10})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "products" in data
        assert len(data["products"]) > 0

        # Check that results contain the search term
        for product in data["products"]:
            assert "name" in product
            # At least some products should contain the search term

    def test_search_products_empty_query(self, client: TestClient):
        """Test searching with empty query"""
        response = client.get("/api/cart/search", params={"query": ""})

        # Should reject empty queries
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_search_products_short_query(self, client: TestClient):
        """Test searching with too short query"""
        response = client.get("/api/cart/search", params={"query": "א"})

        # Should reject queries shorter than 2 characters
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_sample_cart(self, client: TestClient):
        """Test getting sample cart for testing"""
        response = client.get("/api/cart/sample")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "city" in data
        assert "items" in data
        assert len(data["items"]) > 0

        # Check item structure
        for item in data["items"]:
            assert "barcode" in item
            assert "quantity" in item
            assert "name" in item

    def test_compare_cart_with_mixed_results(self, client: TestClient, test_branches: dict, test_products: dict):
        """Test cart comparison where different stores have different availability"""
        cart_data = {
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 1},  # Available everywhere
                {"barcode": "7290000000005", "quantity": 1}   # May not be available everywhere
            ]
        }

        response = client.post("/api/cart/compare", json=cart_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should handle mixed availability gracefully
        assert data["success"] is True
        assert len(data["all_stores"]) > 0

        # Stores might have different available/missing counts
        for store in data["all_stores"]:
            assert store["available_items"] + store["missing_items"] == 2

    def test_compare_cart_hebrew_handling(self, client: TestClient, test_prices: dict):
        """Test that Hebrew text is properly handled in cart comparison"""
        cart_data = {
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 1, "name": "חלב טרה 3%"}
            ]
        }

        response = client.post("/api/cart/compare", json=cart_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Hebrew city name should work
        assert data["city"] == "תל אביב"

        # Hebrew product names should be preserved
        if data["all_stores"] and data["all_stores"][0].get("items_detail"):
            items = data["all_stores"][0]["items_detail"]
            # Check that Hebrew names are preserved
            assert any(item for item in items if "חלב" in str(item.get("name", "")))

    def test_compare_large_cart(self, client: TestClient, test_prices: dict):
        """Test comparing a large cart"""
        # Create a cart with many items
        cart_data = {
            "city": "תל אביב",
            "items": [
                {"barcode": f"729000000000{i}", "quantity": i % 3 + 1}
                for i in range(1, 11)  # 10 items
            ]
        }

        response = client.post("/api/cart/compare", json=cart_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total_items"] == 10

        # Should handle large carts efficiently
        assert "cheapest_store" in data
        assert "all_stores" in data
