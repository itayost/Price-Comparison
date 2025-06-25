"""
API tests for saved carts endpoints.

Tests the /api/saved-carts/* endpoints including saving, listing, and managing carts.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import json

from database.new_models import User, SavedCart
from tests.fixtures.sample_products import SAMPLE_CART_ITEMS


class TestSavedCartsEndpoints:
    """Test saved carts API endpoints"""

    def test_save_cart_success(self, client: TestClient, auth_headers: dict):
        """Test successfully saving a cart"""
        cart_data = {
            "cart_name": "My Weekly Shopping",
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 2, "name": "חלב"},
                {"barcode": "7290000000002", "quantity": 1, "name": "לחם"}
            ]
        }

        response = client.post("/api/saved-carts/save", json=cart_data, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "cart_id" in data
        assert data["message"] == "Cart 'My Weekly Shopping' saved successfully"

    def test_save_cart_unauthorized(self, client: TestClient):
        """Test saving cart without authentication"""
        cart_data = {
            "cart_name": "Test Cart",
            "city": "תל אביב",
            "items": [{"barcode": "7290000000001", "quantity": 1}]
        }

        response = client.post("/api/saved-carts/save", json=cart_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_save_cart_update_existing(self, client: TestClient, auth_headers: dict, db_session: Session):
        """Test updating an existing cart with the same name"""
        cart_data = {
            "cart_name": "Duplicate Cart",
            "city": "תל אביב",
            "items": [{"barcode": "7290000000001", "quantity": 1}]
        }

        # Save first time
        response1 = client.post("/api/saved-carts/save", json=cart_data, headers=auth_headers)
        assert response1.status_code == status.HTTP_200_OK
        cart_id1 = response1.json()["cart_id"]

        # Update with new items
        cart_data["items"] = [
            {"barcode": "7290000000001", "quantity": 2},
            {"barcode": "7290000000002", "quantity": 1}
        ]

        response2 = client.post("/api/saved-carts/save", json=cart_data, headers=auth_headers)
        assert response2.status_code == status.HTTP_200_OK
        cart_id2 = response2.json()["cart_id"]

        # Should be the same cart ID (updated, not new)
        assert cart_id1 == cart_id2

    def test_save_cart_empty_name(self, client: TestClient, auth_headers: dict):
        """Test saving cart with empty name"""
        cart_data = {
            "cart_name": "",
            "city": "תל אביב",
            "items": [{"barcode": "7290000000001", "quantity": 1}]
        }

        response = client.post("/api/saved-carts/save", json=cart_data, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_save_cart_long_name(self, client: TestClient, auth_headers: dict):
        """Test saving cart with name exceeding limit"""
        cart_data = {
            "cart_name": "a" * 101,  # Exceeds 100 character limit
            "city": "תל אביב",
            "items": [{"barcode": "7290000000001", "quantity": 1}]
        }

        response = client.post("/api/saved-carts/save", json=cart_data, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_user_carts(self, client: TestClient, auth_headers: dict, db_session: Session):
        """Test listing user's saved carts"""
        # Save some carts first
        carts_data = [
            {
                "cart_name": "Cart 1",
                "city": "תל אביב",
                "items": [{"barcode": "7290000000001", "quantity": 1}]
            },
            {
                "cart_name": "Cart 2",
                "city": "חיפה",
                "items": [
                    {"barcode": "7290000000001", "quantity": 2},
                    {"barcode": "7290000000002", "quantity": 1}
                ]
            }
        ]

        for cart_data in carts_data:
            client.post("/api/saved-carts/save", json=cart_data, headers=auth_headers)

        # List carts
        response = client.get("/api/saved-carts/list", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 2

        # Check cart structure
        for cart in data:
            assert "cart_id" in cart
            assert "cart_name" in cart
            assert "city" in cart
            assert "item_count" in cart
            assert "created_at" in cart
            assert "updated_at" in cart

        # Verify our carts are in the list
        cart_names = [cart["cart_name"] for cart in data]
        assert "Cart 1" in cart_names
        assert "Cart 2" in cart_names

    def test_list_carts_empty(self, client: TestClient, auth_headers: dict):
        """Test listing carts when user has none"""
        # Create a new user with no carts
        new_user_response = client.post(
            "/api/auth/register",
            json={"email": "nocarts@example.com", "password": "password123"}
        )

        login_response = client.post(
            "/api/auth/login",
            data={"username": "nocarts@example.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        new_headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/saved-carts/list", headers=new_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_compare_saved_cart(self, client: TestClient, auth_headers: dict, test_prices: dict):
        """Test comparing prices for a saved cart"""
        # Save a cart
        cart_data = {
            "cart_name": "Cart to Compare",
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 2},
                {"barcode": "7290000000002", "quantity": 1}
            ]
        }

        save_response = client.post("/api/saved-carts/save", json=cart_data, headers=auth_headers)
        cart_id = save_response.json()["cart_id"]

        # Compare the saved cart
        response = client.get(f"/api/saved-carts/{cart_id}/compare", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "cart_info" in data
        assert "items" in data
        assert "comparison" in data

        # Check comparison results
        comparison = data["comparison"]
        assert "total_items" in comparison
        assert "cheapest_store" in comparison

    def test_compare_saved_cart_not_found(self, client: TestClient, auth_headers: dict):
        """Test comparing non-existent cart"""
        response = client.get("/api/saved-carts/99999/compare", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_delete_cart(self, client: TestClient, auth_headers: dict):
        """Test deleting a saved cart"""
        # Save a cart
        cart_data = {
            "cart_name": "Cart to Delete",
            "city": "תל אביב",
            "items": [{"barcode": "7290000000001", "quantity": 1}]
        }

        save_response = client.post("/api/saved-carts/save", json=cart_data, headers=auth_headers)
        cart_id = save_response.json()["cart_id"]

        # Delete the cart
        response = client.delete(f"/api/saved-carts/{cart_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Cart deleted successfully"

        # Verify it's deleted
        get_response = client.get(f"/api/saved-carts/{cart_id}/compare", headers=auth_headers)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_nonexistent_cart(self, client: TestClient, auth_headers: dict):
        """Test deleting a cart that doesn't exist"""
        response = client.delete("/api/saved-carts/99999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_save_cart_hebrew_handling(self, client: TestClient, auth_headers: dict):
        """Test that Hebrew text is properly saved and retrieved"""
        cart_data = {
            "cart_name": "הקניות השבועיות שלי",
            "city": "ירושלים",
            "items": [
                {"barcode": "7290000000001", "quantity": 2, "name": "חלב טרה 3%"},
                {"barcode": "7290000000002", "quantity": 1, "name": "לחם אחיד פרוס"}
            ]
        }

        # Save cart
        save_response = client.post("/api/saved-carts/save", json=cart_data, headers=auth_headers)
        cart_id = save_response.json()["cart_id"]

        # Get cart details by comparing it
        get_response = client.get(f"/api/saved-carts/{cart_id}/compare", headers=auth_headers)
        data = get_response.json()

        # Verify Hebrew text is preserved
        assert data["cart_info"]["cart_name"] == "הקניות השבועיות שלי"
        assert data["cart_info"]["city"] == "ירושלים"
        assert any(item["name"] == "חלב טרה 3%" for item in data["items"])

    def test_save_large_cart(self, client: TestClient, auth_headers: dict):
        """Test saving a cart with many items"""
        items = [
            {"barcode": f"729000000000{i}", "quantity": i % 5 + 1, "name": f"מוצר {i}"}
            for i in range(1, 51)  # 50 items
        ]

        cart_data = {
            "cart_name": "Large Cart",
            "city": "תל אביב",
            "items": items
        }

        response = client.post("/api/saved-carts/save", json=cart_data, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK

        # Verify it saved correctly
        cart_id = response.json()["cart_id"]
        list_response = client.get("/api/saved-carts/list", headers=auth_headers)

        carts = list_response.json()
        large_cart = next(cart for cart in carts if cart["cart_name"] == "Large Cart")
        assert large_cart["item_count"] == 50

    def test_cart_ownership(self, client: TestClient, auth_headers: dict, db_session: Session):
        """Test that users can't access other users' carts"""
        # Create another user
        other_user_response = client.post(
            "/api/auth/register",
            json={"email": "otheruser@example.com", "password": "password123"}
        )

        other_login = client.post(
            "/api/auth/login",
            data={"username": "otheruser@example.com", "password": "password123"}
        )
        other_token = other_login.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        # Save a cart as the other user
        cart_data = {
            "cart_name": "Other User's Cart",
            "city": "תל אביב",
            "items": [{"barcode": "7290000000001", "quantity": 1}]
        }

        save_response = client.post("/api/saved-carts/save", json=cart_data, headers=other_headers)
        cart_id = save_response.json()["cart_id"]

        # Try to access with original user's token
        response = client.get(f"/api/saved-carts/{cart_id}/compare", headers=auth_headers)

        # Should not find the cart (returns 404, not 403 for security)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Try to delete with original user's token
        delete_response = client.delete(f"/api/saved-carts/{cart_id}", headers=auth_headers)
        assert delete_response.status_code == status.HTTP_404_NOT_FOUND
