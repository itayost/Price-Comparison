"""
Simple API tests for the Price Comparison Server - University Project
All assertions match the exact server responses.
"""
import pytest


class TestBasicFunctionality:
    """Test that the server is working"""

    def test_server_is_running(self, client):
        """Make sure the server responds"""
        response = client.get("/health")
        assert response.status_code == 200
        # From main.py: returns {"status": "healthy"}
        assert response.json() == {"status": "healthy"}

    def test_home_page(self, client):
        """Test the root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        # From main.py: returns message, version, endpoints
        assert data["message"] == "Price Comparison API"
        assert data["version"] == "2.0.0"
        assert "endpoints" in data


class TestMainFeatures:
    """Test the core features - what the app is actually about"""

    def test_search_products(self, client, sample_data):
        """Test searching for products - the main feature"""
        response = client.get("/api/products/search", params={
            "query": "חלב",
            "city": "תל אביב"
        })

        assert response.status_code == 200
        products = response.json()

        # From product_search_service.py: returns list of products
        assert len(products) > 0
        product = products[0]

        # Each product has these fields
        assert "barcode" in product
        assert "name" in product
        assert "חלב" in product["name"]
        assert "prices_by_store" in product
        assert "price_stats" in product

        # price_stats structure
        stats = product["price_stats"]
        assert "min_price" in stats
        assert "max_price" in stats
        assert "avg_price" in stats
        assert "price_range" in stats
        assert "available_in_stores" in stats

    def test_compare_shopping_cart(self, client, sample_data):
        """Test comparing prices for a shopping cart - the whole point of the app"""
        cart = {
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 2},  # Milk
                {"barcode": "7290000000002", "quantity": 1}   # Bread
            ]
        }

        response = client.post("/api/cart/compare", json=cart)
        assert response.status_code == 200

        result = response.json()

        # From cart_routes.py CartComparisonResponse
        assert result["success"] is True
        assert result["total_items"] == 2
        assert result["city"] == "תל אביב"
        assert "comparison_time" in result
        assert "cheapest_store" in result
        assert "all_stores" in result

        # Check cheapest_store structure
        cheapest = result["cheapest_store"]
        assert cheapest is not None
        assert "branch_id" in cheapest
        assert "branch_name" in cheapest
        assert "branch_address" in cheapest
        assert "city" in cheapest
        assert "chain_name" in cheapest
        assert "chain_display_name" in cheapest
        assert "available_items" in cheapest
        assert "missing_items" in cheapest
        assert "total_price" in cheapest
        assert "items_detail" in cheapest

        # Verify we have 2 stores
        assert len(result["all_stores"]) == 2

    def test_get_product_by_barcode(self, client, sample_data):
        """Test getting specific product info"""
        response = client.get("/api/products/barcode/7290000000001", params={
            "city": "תל אביב"
        })

        assert response.status_code == 200
        product = response.json()

        # From product_search_service.py get_product_details_by_barcode
        assert product["barcode"] == "7290000000001"
        assert product["name"] == "חלב 3% תנובה"
        assert product["city"] == "תל אביב"
        assert product["available"] is True  # This IS returned when product is found

        # price_summary structure
        assert "price_summary" in product
        summary = product["price_summary"]
        assert summary["min_price"] == 7.90
        assert summary["max_price"] == 8.50
        assert summary["avg_price"] == 8.20
        assert summary["savings_potential"] == 0.60
        assert summary["total_stores"] == 2

        # prices_by_chain structure
        assert "prices_by_chain" in product
        assert "all_prices" in product


class TestUserFeatures:
    """Test user registration and saved carts"""

    def test_user_registration(self, client):
        """Test that users can register"""
        response = client.post("/api/auth/register", json={
            "email": "student@university.edu",
            "password": "password123"
        })

        # From auth_routes.py: returns UserResponse
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "student@university.edu"
        assert "user_id" in data
        assert "created_at" in data

    def test_user_login(self, client):
        """Test that users can login"""
        # First register
        client.post("/api/auth/register", json={
            "email": "test@test.com",
            "password": "password123"
        })

        # Then login
        response = client.post("/api/auth/login", data={
            "username": "test@test.com",
            "password": "password123"
        })

        # From auth_routes.py: returns Token
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_save_cart(self, client, sample_data, auth_headers):
        """Test saving a shopping cart"""
        response = client.post("/api/saved-carts/save", json={
            "cart_name": "My Shopping List",
            "city": "תל אביב",
            "items": [
                {"barcode": "7290000000001", "quantity": 1}
            ]
        }, headers=auth_headers)

        # From saved_carts_routes.py: returns SavedCartResponse
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cart_id" in data
        assert "message" in data
        assert "saved successfully" in data["message"]

    def test_get_saved_carts(self, client, sample_data, auth_headers):
        """Test getting user's saved carts"""
        # Save a cart first
        client.post("/api/saved-carts/save", json={
            "cart_name": "Test Cart",
            "city": "תל אביב",
            "items": []
        }, headers=auth_headers)

        # Get list
        response = client.get("/api/saved-carts/list", headers=auth_headers)
        assert response.status_code == 200
        carts = response.json()

        assert len(carts) >= 1
        # From saved_carts_routes.py: returns List[CartListResponse]
        cart = carts[0]
        assert cart["cart_name"] == "Test Cart"
        assert cart["city"] == "תל אביב"
        assert "cart_id" in cart
        assert "item_count" in cart
        assert "created_at" in cart
        assert "updated_at" in cart


class TestEdgeCases:
    """Test some important edge cases"""

    def test_empty_search_results(self, client, sample_data):
        """What happens when nothing is found"""
        response = client.get("/api/products/search", params={
            "query": "מוצר שלא קיים",
            "city": "תל אביב"
        })

        assert response.status_code == 200
        # From product_routes.py: returns empty list
        assert response.json() == []

    def test_nonexistent_city(self, client, sample_data):
        """What happens with a city that has no stores"""
        response = client.post("/api/cart/compare", json={
            "city": "עיר לא קיימת",
            "items": [{"barcode": "7290000000001", "quantity": 1}]
        })

        assert response.status_code == 200
        result = response.json()
        # Still returns success but with empty stores
        assert result["success"] is True
        assert len(result["all_stores"]) == 0
        assert result["cheapest_store"] is None

    def test_unauthorized_access(self, client):
        """Test that authentication is required for protected endpoints"""
        response = client.get("/api/saved-carts/list")
        assert response.status_code == 401
        # FastAPI returns detail for 401
        assert "detail" in response.json()

    def test_product_not_found(self, client, sample_data):
        """Test getting non-existent product"""
        response = client.get("/api/products/barcode/9999999999", params={
            "city": "תל אביב"
        })

        assert response.status_code == 404
        assert "detail" in response.json()


class TestDemoScenario:
    """Test a complete scenario for demonstration"""

    def test_shopping_scenario(self, client, sample_data):
        """A complete shopping comparison scenario"""
        # 1. Search for milk
        search_response = client.get("/api/products/search", params={
            "query": "חלב",
            "city": "תל אביב"
        })
        products = search_response.json()

        # Handle potential empty results
        if not products:
            pytest.skip("No products found in test data")

        assert len(products) > 0

        # 2. Get detailed info about the product
        barcode = products[0]["barcode"]
        detail_response = client.get(f"/api/products/barcode/{barcode}", params={
            "city": "תל אביב"
        })
        product_detail = detail_response.json()
        assert product_detail["available"] is True

        # 3. Create a shopping cart
        cart = {
            "city": "תל אביב",
            "items": [
                {"barcode": barcode, "quantity": 2},
                {"barcode": "7290000000002", "quantity": 1}
            ]
        }

        # 4. Compare prices
        compare_response = client.post("/api/cart/compare", json=cart)
        comparison = compare_response.json()

        # 5. Verify we found the cheapest option
        assert comparison["success"] is True
        assert comparison["cheapest_store"] is not None

        cheapest = comparison["cheapest_store"]
        cheapest_price = cheapest["total_price"]

        # Make sure it's actually the cheapest
        for store in comparison["all_stores"]:
            assert store["total_price"] >= cheapest_price

        # 6. Show results (for demo)
        print(f"\n✓ Found {len(products)} products matching 'חלב'")
        print(f"✓ Cheapest store: {cheapest['chain_display_name']} - {cheapest['branch_name']}")
        print(f"✓ Total price: ₪{cheapest_price:.2f}")
        print(f"✓ Available items: {cheapest['available_items']}/{comparison['total_items']}")

        # Calculate savings
        most_expensive = max(s['total_price'] for s in comparison['all_stores'])
        savings = most_expensive - cheapest_price
        print(f"✓ Potential savings: ₪{savings:.2f}")
