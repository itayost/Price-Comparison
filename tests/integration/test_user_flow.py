"""
Integration tests for complete user flows.

Tests end-to-end user journeys through the application.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import time

from database.new_models import User, SavedCart


class TestUserFlow:
    """Test complete user journeys through the application"""
    
    def test_new_user_complete_flow(self, client: TestClient, test_prices: dict):
        """Test complete flow for a new user: register, login, search, compare, save cart"""
        # Step 1: Register new user
        registration_data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!"
        }
        
        register_response = client.post("/api/auth/register", json=registration_data)
        assert register_response.status_code == status.HTTP_200_OK
        user_id = register_response.json()["user_id"]
        
        # Step 2: Login
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": registration_data["email"],
                "password": registration_data["password"]
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: Verify authentication
        me_response = client.get("/api/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["email"] == registration_data["email"]
        
        # Step 4: Search for products
        search_response = client.get(
            "/api/products/search",
            params={"query": "חלב", "city": "תל אביב"}
        )
        assert search_response.status_code == status.HTTP_200_OK
        products = search_response.json()
        assert len(products) > 0
        
        # Step 5: Get detailed product information
        barcode = products[0]["barcode"]
        product_response = client.get(
            f"/api/products/barcode/{barcode}",
            params={"city": "תל אביב"}
        )
        assert product_response.status_code == status.HTTP_200_OK
        
        # Step 6: Compare cart prices
        cart_data = {
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 2},
                {"barcode": "7290000000002", "quantity": 1},
                {"barcode": "7290000000003", "quantity": 1}
            ]
        }
        
        compare_response = client.post("/api/cart/compare", json=cart_data)
        assert compare_response.status_code == status.HTTP_200_OK
        comparison = compare_response.json()
        assert comparison["success"] is True
        assert comparison["cheapest_store"] is not None
        
        # Step 7: Save the cart
        save_cart_data = {
            "cart_name": "My First Cart",
            "city": "תל אביב",
            "items": cart_data["items"]
        }
        
        save_response = client.post(
            "/api/saved-carts/save",
            json=save_cart_data,
            headers=headers
        )
        assert save_response.status_code == status.HTTP_200_OK
        cart_id = save_response.json()["cart_id"]
        
        # Step 8: List saved carts
        list_response = client.get("/api/saved-carts/list", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        carts = list_response.json()
        assert len(carts) >= 1
        assert any(cart["cart_name"] == "My First Cart" for cart in carts)
        
        # Step 9: Compare saved cart
        saved_compare_response = client.get(
            f"/api/saved-carts/{cart_id}/compare",
            headers=headers
        )
        assert saved_compare_response.status_code == status.HTTP_200_OK
        saved_comparison = saved_compare_response.json()
        assert saved_comparison["success"] is True
    
    def test_returning_user_flow(self, client: TestClient, test_user: User, test_prices: dict):
        """Test flow for returning user with existing data"""
        # Step 1: Login as existing user
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "testpass123"
            }
        )
        assert login_response.status_code == status.HTTP_200_OK
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Create multiple saved carts
        cart_names = ["Weekly Shopping", "Party Supplies", "Quick Essentials"]
        cart_ids = []
        
        for name in cart_names:
            save_response = client.post(
                "/api/saved-carts/save",
                json={
                    "cart_name": name,
                    "city": "תל אביב",
                    "items": [
                        {"barcode": "7290000000001", "quantity": 2},
                        {"barcode": "7290000000002", "quantity": 1}
                    ]
                },
                headers=headers
            )
            assert save_response.status_code == status.HTTP_200_OK
            cart_ids.append(save_response.json()["cart_id"])
        
        # Step 3: List all carts
        list_response = client.get("/api/saved-carts/list", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        carts = list_response.json()
        assert len(carts) >= 3
        
        # Step 4: Update one cart
        update_response = client.post(
            "/api/saved-carts/save",
            json={
                "cart_name": "Weekly Shopping",  # Same name - should update
                "city": "תל אביב",
                "items": [
                    {"barcode": "7290000000001", "quantity": 3},  # Changed quantity
                    {"barcode": "7290000000002", "quantity": 2},
                    {"barcode": "7290000000003", "quantity": 1}   # Added item
                ]
            },
            headers=headers
        )
        assert update_response.status_code == status.HTTP_200_OK
        
        # Step 5: Verify update
        updated_cart_response = client.get(
            f"/api/saved-carts/{cart_ids[0]}",
            headers=headers
        )
        assert updated_cart_response.status_code == status.HTTP_200_OK
        updated_cart = updated_cart_response.json()["cart"]
        assert len(updated_cart["items"]) == 3
        
        # Step 6: Delete a cart
        delete_response = client.delete(
            f"/api/saved-carts/{cart_ids[2]}",
            headers=headers
        )
        assert delete_response.status_code == status.HTTP_200_OK
        
        # Step 7: Verify deletion
        final_list_response = client.get("/api/saved-carts/list", headers=headers)
        final_carts = final_list_response.json()
        cart_names_after = [cart["cart_name"] for cart in final_carts]
        assert "Quick Essentials" not in cart_names_after
    
    def test_multi_city_shopping_flow(self, client: TestClient, auth_headers: dict, test_branches: dict):
        """Test user shopping in multiple cities"""
        cities = ["תל אביב", "חיפה"]
        
        for city in cities:
            # Step 1: Check available branches
            branches_response = client.get(f"/api/products/branches/{city}")
            if branches_response.status_code == status.HTTP_200_OK:
                branches = branches_response.json()
                
                if len(branches) > 0:
                    # Step 2: Search products in this city
                    search_response = client.get(
                        "/api/products/search",
                        params={"query": "חלב", "city": city}
                    )
                    assert search_response.status_code == status.HTTP_200_OK
                    
                    # Step 3: Compare cart in this city
                    cart_data = {
                        "city": city,
                        "items": [
                            {"barcode": "7290000000001", "quantity": 1},
                            {"barcode": "7290000000002", "quantity": 1}
                        ]
                    }
                    
                    compare_response = client.post("/api/cart/compare", json=cart_data)
                    assert compare_response.status_code == status.HTTP_200_OK
                    
                    # Step 4: Save cart for this city
                    save_response = client.post(
                        "/api/saved-carts/save",
                        json={
                            "cart_name": f"Shopping in {city}",
                            "city": city,
                            "items": cart_data["items"]
                        },
                        headers=auth_headers
                    )
                    assert save_response.status_code == status.HTTP_200_OK
    
    def test_price_comparison_decision_flow(self, client: TestClient, test_prices: dict):
        """Test user making decisions based on price comparisons"""
        # Step 1: Compare a basic cart
        basic_cart = {
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 1},
                {"barcode": "7290000000002", "quantity": 1}
            ]
        }
        
        basic_response = client.post("/api/cart/compare", json=basic_cart)
        assert basic_response.status_code == status.HTTP_200_OK
        basic_comparison = basic_response.json()
        
        # Step 2: Add more items and compare again
        expanded_cart = {
            "city": "תל אביב",
            "items": basic_cart["items"] + [
                {"barcode": "7290000000003", "quantity": 2},
                {"barcode": "7290000000004", "quantity": 1}
            ]
        }
        
        expanded_response = client.post("/api/cart/compare", json=expanded_cart)
        assert expanded_response.status_code == status.HTTP_200_OK
        expanded_comparison = expanded_response.json()
        
        # Step 3: Check if cheapest store changed
        if (basic_comparison["cheapest_store"] and 
            expanded_comparison["cheapest_store"]):
            # User might need to reconsider which store to visit
            basic_cheapest = basic_comparison["cheapest_store"]["chain_name"]
            expanded_cheapest = expanded_comparison["cheapest_store"]["chain_name"]
            
            # This simulates user decision-making based on results
            if basic_cheapest != expanded_cheapest:
                # User realizes different store is better for larger cart
                pass
        
        # Step 4: Check individual product prices
        for barcode in ["7290000000001", "7290000000002"]:
            product_response = client.get(
                f"/api/cart/product/{barcode}"
            )
            if product_response.status_code == status.HTTP_200_OK:
                product_data = product_response.json()
                # User can see price variations across stores
    
    def test_performance_user_flow(self, client: TestClient, auth_headers: dict, test_prices: dict):
        """Test system performance with typical user actions"""
        start_time = time.time()
        
        # Rapid sequential searches
        search_terms = ["חלב", "לחם", "ביצים", "גבינה", "עגבניות"]
        for term in search_terms:
            response = client.get(
                "/api/products/search",
                params={"query": term, "city": "תל אביב", "limit": 10}
            )
            assert response.status_code == status.HTTP_200_OK
        
        search_time = time.time() - start_time
        assert search_time < 5.0  # All searches should complete within 5 seconds
        
        # Multiple cart comparisons
        start_time = time.time()
        for i in range(5):
            cart_data = {
                "city": "תל אביב",
                "items": [
                    {"barcode": f"729000000000{j}", "quantity": j % 3 + 1}
                    for j in range(1, 6)
                ]
            }
            response = client.post("/api/cart/compare", json=cart_data)
            assert response.status_code == status.HTTP_200_OK
        
        compare_time = time.time() - start_time
        assert compare_time < 10.0  # All comparisons should complete within 10 seconds
    
    def test_error_recovery_flow(self, client: TestClient, auth_headers: dict):
        """Test user experience when encountering errors"""
        # Step 1: Try to save cart with invalid data
        invalid_cart = {
            "cart_name": "",  # Invalid
            "city": "תל אביב",
            "items": []
        }
        
        response = client.post(
            "/api/saved-carts/save",
            json=invalid_cart,
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Step 2: Correct the errors and retry
        valid_cart = {
            "cart_name": "Corrected Cart",
            "city": "תל אביב",
            "items": [{"barcode": "7290000000001", "quantity": 1}]
        }
        
        retry_response = client.post(
            "/api/saved-carts/save",
            json=valid_cart,
            headers=auth_headers
        )
        assert retry_response.status_code == status.HTTP_200_OK
        
        # Step 3: Try to access non-existent resource
        response = client.get("/api/saved-carts/99999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Step 4: Continue with valid operations
        list_response = client.get("/api/saved-carts/list", headers=auth_headers)
        assert list_response.status_code == status.HTTP_200_OK
