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
    # Shufersal has the cheaper price (5.90 vs 6.20)
    assert data["cheapest_store"]["chain_name"] == "shufersal"
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

    # Should still return results for available products
    assert data["success"] == True
    assert data["cheapest_store"] is not None
    assert data["cheapest_store"]["available_items"] >= 1
    assert data["cheapest_store"]["missing_items"] >= 0

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
    # No stores in non-existent city
    assert data["cheapest_store"] is None
    assert len(data["all_stores"]) == 0

def test_compare_multiple_items(client, sample_data):
    """Test comparing cart with multiple items"""
    cart_data = {
        "city": "תל אביב",
        "items": [
            {"barcode": "7290000000001", "quantity": 1},  # Milk
            {"barcode": "7290000000002", "quantity": 2}   # Bread
        ]
    }

    response = client.post("/api/cart/compare", json=cart_data)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] == True
    assert data["total_items"] == 2
    assert data["cheapest_store"] is not None
    # Victory has cheaper bread (6.90 vs 7.50) but more expensive milk
    # Need to check which store is actually cheaper overall
