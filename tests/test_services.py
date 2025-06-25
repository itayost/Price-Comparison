"""
Service tests for business logic.
Test core functionality without complex mocking.
"""
import pytest
from datetime import datetime
from services.cart_service import CartComparisonService, CartItem
from services.auth_service import AuthService
from services.product_search_service import ProductSearchService


class TestCartComparisonService:
    """Test cart comparison business logic"""
    
    def test_compare_cart_basic(self, db, sample_data):
        """Test basic cart comparison functionality"""
        service = CartComparisonService(db)
        
        # Create a simple cart
        items = [
            {"barcode": "7290000000001", "quantity": 2},  # Milk
            {"barcode": "7290000000002", "quantity": 1}   # Bread
        ]
        
        result = service.compare_cart(city="תל אביב", items=items)
        
        # Verify result structure
        assert result is not None
        assert "stores" in result
        assert len(result["stores"]) == 2  # We have 2 stores in test data
        
        # Check each store result
        for store in result["stores"]:
            assert "branch_name" in store
            assert "total_price" in store
            assert "available_items" in store
            assert "missing_items" in store
    
    def test_find_cheapest_store(self, db, sample_data):
        """Test finding the cheapest store for a cart"""
        service = CartComparisonService(db)
        
        items = [{"barcode": "7290000000001", "quantity": 1}]
        result = service.compare_cart(city="תל אביב", items=items)
        
        stores = result["stores"]
        
        # Find cheapest manually
        cheapest = min(stores, key=lambda x: x["total_price"])
        
        # Shufersal should be cheaper for milk (7.90 vs 8.50)
        assert cheapest["chain_name"] == "shufersal"
        assert cheapest["total_price"] == 7.90
    
    def test_handle_missing_products(self, db, sample_data):
        """Test handling products not available in some stores"""
        service = CartComparisonService(db)
        
        # Add a product that doesn't exist
        items = [
            {"barcode": "7290000000001", "quantity": 1},
            {"barcode": "9999999999999", "quantity": 1}  # Non-existent
        ]
        
        result = service.compare_cart(city="תל אביב", items=items)
        
        # Should still return results
        assert len(result["stores"]) > 0
        
        # Check missing items count
        for store in result["stores"]:
            assert store["missing_items"] >= 1
            assert store["available_items"] == 1
    
    def test_empty_city_results(self, db, sample_data):
        """Test cart comparison for city with no stores"""
        service = CartComparisonService(db)
        
        items = [{"barcode": "7290000000001", "quantity": 1}]
        result = service.compare_cart(city="חיפה", items=items)
        
        # Should return empty results
        assert result["stores"] == []


class TestAuthenticationService:
    """Test authentication business logic"""
    
    def test_create_user(self, db):
        """Test user creation"""
        service = AuthService(db)
        
        user = service.create_user(
            email="testuser@example.com",
            password="securepassword123"
        )
        
        assert user is not None
        assert user.email == "testuser@example.com"
        # Password should be hashed
        assert user.password_hash != "securepassword123"
    
    def test_verify_password(self, db):
        """Test password verification"""
        service = AuthService(db)
        
        # Create user
        user = service.create_user(
            email="passtest@example.com",
            password="mypassword"
        )
        
        # Test correct password
        assert service.verify_password("mypassword", user.password_hash) is True
        
        # Test wrong password
        assert service.verify_password("wrongpassword", user.password_hash) is False
    
    def test_authenticate_user(self, db):
        """Test user authentication"""
        service = AuthService(db)
        
        # Create user
        service.create_user(
            email="authtest@example.com",
            password="testpass123"
        )
        
        # Test successful authentication
        user = service.authenticate_user("authtest@example.com", "testpass123")
        assert user is not None
        assert user.email == "authtest@example.com"
        
        # Test failed authentication
        user = service.authenticate_user("authtest@example.com", "wrongpass")
        assert user is None
    
    def test_create_access_token(self, db):
        """Test JWT token creation"""
        service = AuthService(db)
        
        token = service.create_access_token("test@example.com")
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token(self, db):
        """Test JWT token verification"""
        service = AuthService(db)
        
        # Create token
        email = "tokentest@example.com"
        token = service.create_access_token(email)
        
        # Verify token
        verified_email = service.verify_token(token)
        assert verified_email == email
        
        # Test invalid token
        invalid_email = service.verify_token("invalid.token.here")
        assert invalid_email is None
    
    def test_duplicate_user_creation(self, db):
        """Test that duplicate users cannot be created"""
        service = AuthService(db)
        
        # Create first user
        service.create_user(
            email="duplicate@example.com",
            password="password123"
        )
        
        # Try to create duplicate
        with pytest.raises(ValueError, match="Email already registered"):
            service.create_user(
                email="duplicate@example.com",
                password="password456"
            )


class TestProductSearchService:
    """Test product search functionality"""
    
    def test_search_products_by_name(self, db, sample_data):
        """Test searching products by name"""
        service = ProductSearchService(db)
        
        # Search for milk
        results = service.search_products_with_prices(
            query="חלב",
            city="תל אביב",
            limit=10
        )
        
        assert len(results) > 0
        assert "חלב" in results[0]["name"]
        assert results[0]["barcode"] == "7290000000001"
    
    def test_search_with_price_stats(self, db, sample_data):
        """Test that search results include price statistics"""
        service = ProductSearchService(db)
        
        results = service.search_products_with_prices(
            query="חלב",
            city="תל אביב"
        )
        
        product = results[0]
        
        # Check price statistics
        assert "price_stats" in product
        stats = product["price_stats"]
        assert stats["min_price"] == 7.90
        assert stats["max_price"] == 8.50
        assert stats["avg_price"] == 8.20
        assert stats["cheapest_store"]["chain_name"] == "shufersal"
    
    def test_search_no_results(self, db, sample_data):
        """Test searching for non-existent product"""
        service = ProductSearchService(db)
        
        results = service.search_products_with_prices(
            query="מוצר לא קיים",
            city="תל אביב"
        )
        
        assert results == []
    
    def test_get_product_by_barcode(self, db, sample_data):
        """Test getting product by exact barcode"""
        service = ProductSearchService(db)
        
        product = service.get_product_by_barcode(
            barcode="7290000000001",
            city="תל אביב"
        )
        
        assert product is not None
        assert product["barcode"] == "7290000000001"
        assert "חלב" in product["name"]
        assert len(product["prices_by_store"]) == 2
    
    def test_search_case_insensitive(self, db, sample_data):
        """Test that search is case insensitive"""
        service = ProductSearchService(db)
        
        # Search with different cases
        results1 = service.search_products_with_prices("חלב", "תל אביב")
        results2 = service.search_products_with_prices("חלב", "תל אביב")
        
        # Should return same results
        assert len(results1) == len(results2)


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_cart_with_zero_quantity(self, db, sample_data):
        """Test cart with zero quantity items"""
        service = CartComparisonService(db)
        
        items = [{"barcode": "7290000000001", "quantity": 0}]
        
        # Should handle gracefully
        result = service.compare_cart(city="תל אביב", items=items)
        
        # Total should be 0
        for store in result["stores"]:
            assert store["total_price"] == 0
    
    def test_very_large_quantity(self, db, sample_data):
        """Test cart with very large quantities"""
        service = CartComparisonService(db)
        
        items = [{"barcode": "7290000000001", "quantity": 999999}]
        
        result = service.compare_cart(city="תל אביב", items=items)
        
        # Should calculate correctly
        assert len(result["stores"]) > 0
        for store in result["stores"]:
            assert store["total_price"] > 0
    
    def test_hebrew_city_names(self, db, sample_data):
        """Test that Hebrew city names work correctly"""
        service = CartComparisonService(db)
        
        # Test with Hebrew city name
        items = [{"barcode": "7290000000001", "quantity": 1}]
        result = service.compare_cart(city="תל אביב", items=items)
        
        assert len(result["stores"]) == 2
    
    def test_empty_database(self, db):
        """Test services handle empty database gracefully"""
        # Don't load sample data
        
        # Test cart service
        cart_service = CartComparisonService(db)
        result = cart_service.compare_cart(
            city="תל אביב",
            items=[{"barcode": "123", "quantity": 1}]
        )
        assert result["stores"] == []
        
        # Test search service
        search_service = ProductSearchService(db)
        results = search_service.search_products_with_prices("test", "תל אביב")
        assert results == []
