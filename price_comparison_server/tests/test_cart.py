# tests/test_cart.py
import pytest

def test_compare_cart_single_item(client, sample_data):
    """Test comparing cart with single item"""
    cart_data = {
        "city": "תל אביב",
        "items": [
            {"barcode": "7290000000001", "quantity": 2}
        ]
    }
    
    response = client.post("/api/cart/compare", json=cart_data)
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] == True
    assert data["total_items"] == 1
    assert data["cheapest_store"] is not None
    assert data["cheapest_store"]["total_price"] == 11.80  # 5.90 * 2

def test_compare_cart_missing_product(client, sample_data):
    """Test cart comparison handles missing products gracefully"""
    cart_data = {
        "city": "תל אביב",
        "items": [
            {"barcode": "7290000000001", "quantity": 1},
            {"barcode": "9999999999999", "quantity": 1}  # Doesn't exist
        ]
    }
    
    response = client.post("/api/cart/compare", json=cart_data)
    assert response.status_code == 200
    data = response.json()
    
    assert data["cheapest_store"]["available_items"] == 1
    assert data["cheapest_store"]["missing_items"] == 1

def test_compare_cart_invalid_city(client, sample_data):
    """Test cart comparison with non-existent city"""
    cart_data = {
        "city": "עיר לא קיימת",
        "items": [
            {"barcode": "7290000000001", "quantity": 1}
        ]
    }
    
    response = client.post("/api/cart/compare", json=cart_data)
    assert response.status_code == 200
    data = response.json()
    assert data["cheapest_store"] is None
