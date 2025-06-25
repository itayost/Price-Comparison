"""
Simplified API tests for the price comparison server.
Focus on testing the main user flows and critical functionality.
"""
import pytest
from fastapi import status


class TestHealthAndBasics:
    """Test basic server functionality"""

    def test_server_is_running(self, client):
        """Test that the server responds to health check"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data


class TestCartComparison:
    """Test the core cart comparison functionality"""

    def test_compare_simple_cart(self, client, sample_data):
        """Test comparing a simple cart with two items"""
        cart_data = {
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 2},  # Milk x2
                {"barcode": "7290000000002", "quantity": 1}   # Bread x1
            ]
        }

        response = client.post("/api/cart/compare", json=cart_data)

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert data["success"] is True
        assert data["total_items"] == 2
        assert data["city"] == "תל אביב"
        assert "cheapest_store" in data
        assert "all_stores" in data

        # Check we got results from both stores
        assert len(data["all_stores"]) == 2

        # Check cheapest store calculation
        # Shufersal: (7.90 * 2) + 5.90 = 21.70
        # Victory: (8.50 * 2) + 5.50 = 22.50
        cheapest = data["cheapest_store"]
        assert cheapest["chain_name"] == "shufersal"
        assert cheapest["total_price"] == 21.70

    def test_compare_empty_cart(self, client):
        """Test comparing an empty cart"""
        cart_data = {
            "city": "תל אביב",
            "items": []
        }

        response = client.post("/api/cart/compare", json=cart_data)

        # Should handle gracefully
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.json()
            assert data["total_items"] == 0

    def test_compare_cart_invalid_city(self, client, sample_data):
        """Test cart comparison with non-existent city"""
        cart_data = {
            "city": "עיר לא קיימת",
            "items": [
                {"barcode": "7290000000001", "quantity": 1}
            ]
        }

        response = client.post("/api/cart/compare", json=cart_data)

        # Should return OK but with no stores
        assert response.status_code == 200
        data = response.json()
        assert len(data["all_stores"]) == 0


class TestProductSearch:
    """Test product search functionality"""

    def test_search_products_hebrew(self, client, sample_data):
        """Test searching for products with Hebrew query"""
        response = client.get("/api/products/search", params={
            "query": "חלב",
            "city": "תל אביב",
            "limit": 10
        })

        assert response.status_code == 200
        products = response.json()

        assert len(products) > 0
        assert "חלב" in products[0]["name"]
        assert "barcode" in products[0]
        assert "prices_by_store" in products[0]

    def test_search_products_no_results(self, client, sample_data):
        """Test searching for non-existent product"""
        response = client.get("/api/products/search", params={
            "query": "מוצר לא קיים",
            "city": "תל אביב"
        })

        assert response.status_code == 200
        products = response.json()
        assert len(products) == 0

    def test_get_product_by_barcode(self, client, sample_data):
        """Test getting specific product by barcode"""
        response = client.get("/api/products/barcode/7290000000001", params={
            "city": "תל אביב"
        })

        assert response.status_code == 200
        product = response.json()

        assert product["barcode"] == "7290000000001"
        assert "חלב" in product["name"]
        assert len(product["prices_by_store"]) == 2


class TestAuthentication:
    """Test user authentication"""

    def test_register_new_user(self, client):
        """Test user registration"""
        user_data = {
            "email": "newuser@test.com",
            "password": "password123"
        }

        response = client.post("/api/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert data["email"] == "newuser@test.com"

    def test_register_duplicate_user(self, client):
        """Test registering with existing email"""
        user_data = {
            "email": "duplicate@test.com",
            "password": "password123"
        }

        # Register first time
        client.post("/api/auth/register", json=user_data)

        # Try to register again
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 400

    def test_login_success(self, client):
        """Test successful login"""
        # First register
        client.post("/api/auth/register", json={
            "email": "login@test.com",
            "password": "password123"
        })

        # Then login
        response = client.post("/api/auth/login", data={
            "username": "login@test.com",
            "password": "password123"
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        """Test login with wrong password"""
        # Register user
        client.post("/api/auth/register", json={
            "email": "wrongpass@test.com",
            "password": "correctpass"
        })

        # Try to login with wrong password
        response = client.post("/api/auth/login", data={
            "username": "wrongpass@test.com",
            "password": "wrongpass"
        })

        assert response.status_code == 401


class TestSavedCarts:
    """Test saved cart functionality"""

    def test_save_cart_authenticated(self, client, sample_data, auth_headers):
        """Test saving a cart (requires authentication)"""
        cart_data = {
            "cart_name": "השופינג השבועי שלי",
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 2, "name": "חלב"},
                {"barcode": "7290000000002", "quantity": 1, "name": "לחם"}
            ]
        }

        response = client.post(
            "/api/saved-carts/save",
            json=cart_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cart_id" in data

    def test_save_cart_unauthenticated(self, client):
        """Test that saving cart requires authentication"""
        cart_data = {
            "cart_name": "Test Cart",
            "city": "תל אביב",
            "items": []
        }

        response = client.post("/api/saved-carts/save", json=cart_data)
        assert response.status_code == 401

    def test_get_user_carts(self, client, sample_data, auth_headers):
        """Test getting user's saved carts"""
        # First save a cart
        client.post("/api/saved-carts/save", json={
            "cart_name": "Cart 1",
            "city": "תל אביב",
            "items": [{"barcode": "7290000000001", "quantity": 1}]
        }, headers=auth_headers)

        # Get user's carts
        response = client.get("/api/saved-carts/my-carts", headers=auth_headers)

        assert response.status_code == 200
        carts = response.json()
        assert len(carts) >= 1
        assert carts[0]["cart_name"] == "Cart 1"


class TestSystemEndpoints:
    """Test system monitoring endpoints"""

    def test_get_available_chains(self, client, sample_data):
        """Test getting list of chains"""
        response = client.get("/api/products/chains")

        assert response.status_code == 200
        chains = response.json()
        assert len(chains) == 2

        # Check chain structure
        for chain in chains:
            assert "chain_id" in chain
            assert "name" in chain
            assert "display_name" in chain
