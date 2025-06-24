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
    assert data[0]["name"] == "חלב 3% טרה 1 ליטר"

def test_search_hebrew_handling(client, sample_data):
    """Test that Hebrew text is handled correctly"""
    response = client.get(
        "/api/products/search",
        params={"query": "חלב", "city": "תל אביב"}
    )
    data = response.json()
    # Verify Hebrew text is preserved correctly
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
    assert data["price_summary"]["min_price"] == 5.90
