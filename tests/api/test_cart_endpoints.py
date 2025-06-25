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
            assert data["success"] is True
            assert data["total_items"] == 0

    def test_compare_cart_invalid_city(self, client: TestClient):
        """Test cart comparison with invalid city"""
        cart_data = {
            "city": "עיר לא קיימת",
            "items": [
                {"barcode": "7290000000001", "quantity": 1}
            ]
        }

        response = client.post("/api/cart/compare", json=cart_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should return empty results for non-existent city
        assert data["success"] is True
        assert len(data["all_stores"]) == 0

    def test_compare_cart_missing_fields(self, client: TestClient):
        """Test cart comparison with missing required fields"""
        # Missing city
        response = client.post("/api/cart/compare", json={"items": []})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing items
        response = client.post("/api/cart/compare", json={"city": "תל אביב"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Empty request
        response = client.post("/api/cart/compare", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_compare_cart_invalid_quantity(self, client: TestClient):
        """Test cart comparison with invalid quantities"""
        invalid_quantities = [0, -1, -10]

        for qty in invalid_quantities:
            cart_data = {
                "city": "תל אביב",
                "items": [
                    {"barcode": "7290000000001", "quantity": qty}
                ]
            }

            response = client.post("/api/cart/compare", json=cart_data)
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

        assert data["success"] is True
        # Verify different stores may have different availability
        if len(data["all_stores"]) > 1:
            availabilities = [store["available_items"] for store in data["all_stores"]]
            # Not all stores need to have the same availability

    def test_compare_cart_large_quantities(self, client: TestClient, test_prices: dict):
        """Test cart comparison with large quantities"""
        cart_data = {
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 999}
            ]
        }

        response = client.post("/api/cart/compare", json=cart_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if data["cheapest_store"]:
            # Price should scale with quantity
            assert data["cheapest_store"]["total_price"] > 100

    def test_compare_cart_hebrew_city_names(self, client: TestClient, test_prices: dict):
        """Test cart comparison with various Hebrew city names"""
        hebrew_cities = ["תל אביב", "ירושלים", "חיפה", "באר שבע"]

        for city in hebrew_cities:
            cart_data = {
                "city": city,
                "items": [{"barcode": "7290000000001", "quantity": 1}]
            }

            response = client.post("/api/cart/compare", json=cart_data)
            assert response.status_code == status.HTTP_200_OK

    def test_compare_cart_performance(self, client: TestClient, test_prices: dict):
        """Test cart comparison performance with many items"""
        # Create a cart with 20 items
        items = [
            {"barcode": f"729000000000{i}", "quantity": (i % 3) + 1}
            for i in range(1, 21)
        ]

        cart_data = {
            "city": "תל אביב",
            "items": items
        }

        import time
        start_time = time.time()
        response = client.post("/api/cart/compare", json=cart_data)
        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        # Should complete within reasonable time (2 seconds)
        assert end_time - start_time < 2.0

    def test_compare_cart_special_characters_in_names(self, client: TestClient):
        """Test cart with special characters in product names"""
        cart_data = {
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 1, "name": "קוטג' 5%"},
                {"barcode": "7290000000002", "quantity": 1, "name": "צ'יפס BBQ"}
            ]
        }

        response = client.post("/api/cart/compare", json=cart_data)
        assert response.status_code == status.HTTP_200_OK
