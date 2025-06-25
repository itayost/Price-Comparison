# tests/test_products.py
import pytest

def test_search_products(client, sample_data):
    """Test searching for products by name"""
    response = client.get(
        "/api/products/search",
        params={"query": "חלב", "city": "תל אביב"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    # Check that we found milk products
    assert any("חלב" in product["name"] for product in data)
    # Check that prices are included
    assert "prices_by_store" in data[0]
    assert len(data[0]["prices_by_store"]) > 0

def test_search_hebrew_handling(client, sample_data):
    """Test that Hebrew text is handled correctly"""
    response = client.get(
        "/api/products/search",
        params={"query": "חלב", "city": "תל אביב"}
    )
    assert response.status_code == 200
    data = response.json()
    # Verify Hebrew text is preserved correctly
    assert len(data) > 0
    assert "חלב" in data[0]["name"]

def test_empty_search_results(client, sample_data):
    """Test searching for non-existent product"""
    response = client.get(
        "/api/products/search",
        params={"query": "מוצר לא קיים", "city": "תל אביב"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

def test_get_product_by_barcode(client, sample_data):
    """Test getting specific product details"""
    response = client.get(
        "/api/products/barcode/7290000000001",
        params={"city": "תל אביב"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["barcode"] == "7290000000001"
    assert data["available"] == True
    # We have two prices for milk (5.90 at Shufersal, 6.20 at Victory)
    assert data["price_summary"]["min_price"] == 5.90
    assert data["price_summary"]["max_price"] == 6.20
    assert data["price_summary"]["total_stores"] == 2

def test_get_nonexistent_product_by_barcode(client, sample_data):
    """Test getting non-existent product returns 404"""
    response = client.get(
        "/api/products/barcode/9999999999999",
        params={"city": "תל אביב"}
    )
    assert response.status_code == 404

def test_product_autocomplete(client, sample_data):
    """Test product name autocomplete"""
    response = client.get(
        "/api/products/autocomplete",
        params={"query": "חל", "limit": 5}
    )
    assert response.status_code == 200
    suggestions = response.json()
    assert len(suggestions) > 0
    # Should return milk products
    assert any("חלב" in suggestion for suggestion in suggestions)
