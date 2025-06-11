from fastapi import APIRouter, HTTPException
import sqlite3
from typing import List
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path for imports if needed
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.data_models import SaveCartRequest
from utils.db_utils import USER_DB
from services.search_service import search_products_by_name_and_city

router = APIRouter(tags=["carts"])

@router.post("/save-cart")
def save_cart(request: SaveCartRequest):
    try:
        conn = sqlite3.connect(USER_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT email FROM users WHERE email = ?", (request.email,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if cart already exists
        cursor.execute("""
            SELECT cart_name FROM carts 
            WHERE email = ? AND cart_name = ?
        """, (request.email, request.cart_name))
        
        if cursor.fetchone():
            # If cart exists, delete it and its items
            cursor.execute("""
                DELETE FROM cart_items WHERE cart_id IN 
                (SELECT id FROM carts WHERE email = ? AND cart_name = ?)
            """, (request.email, request.cart_name))
            
            cursor.execute("""
                DELETE FROM carts WHERE email = ? AND cart_name = ?
            """, (request.email, request.cart_name))
        
        # Create new cart
        cursor.execute("""
            INSERT INTO carts (email, cart_name, city) VALUES (?, ?, ?)
        """, (request.email, request.cart_name, request.city))
        
        cart_id = cursor.lastrowid
        
        # Insert cart items
        for item in request.items:
            cursor.execute("""
                INSERT INTO cart_items (cart_id, item_name, quantity) VALUES (?, ?, ?)
            """, (cart_id, item.item_name, item.quantity))
        
        conn.commit()
        conn.close()
        
        return {"message": "Cart saved successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/savedcarts/{email}")
def get_saved_carts(email: str, city: str = None):
    try:
        logger.info(f"Getting saved carts for email: {email}, city: {city}")
        conn = sqlite3.connect(USER_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
        if not cursor.fetchone():
            logger.warning(f"User not found: {email}")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user's saved carts
        if city:
            logger.info(f"Filtering carts by city: {city}")
            cursor.execute("""
                SELECT id, cart_name, city FROM carts WHERE email = ? AND city = ?
            """, (email, city))
        else:
            logger.info("Getting all carts (no city filter)")
            cursor.execute("""
                SELECT id, cart_name, city FROM carts WHERE email = ?
            """, (email,))
        
        cart_rows = cursor.fetchall()
        logger.info(f"Found {len(cart_rows)} carts")
        
        carts = []
        for cart_row in cart_rows:
            cart_id = cart_row["id"]
            cart_name = cart_row["cart_name"]
            cart_city = cart_row.get("city", city)
            logger.info(f"Processing cart: {cart_name} (ID: {cart_id}, City: {cart_city})")
            
            # Get items for this cart
            cursor.execute("""
                SELECT item_name, quantity FROM cart_items WHERE cart_id = ?
            """, (cart_id,))
            
            item_rows = cursor.fetchall()
            logger.info(f"Found {len(item_rows)} items in cart {cart_name}")
            
            items = []
            for item_row in item_rows:
                item = dict(item_row)
                logger.info(f"Processing item: {item['item_name']} (Qty: {item['quantity']})")
                
                # Try to get current price for this item
                cart_city = cart_city or city  # Use cart-specific city or the query parameter
                if cart_city:
                    try:
                        logger.info(f"Searching for prices for {item['item_name']} in {cart_city}")
                        search_results = search_products_by_name_and_city(cart_city, item["item_name"])
                        logger.info(f"Found {len(search_results)} results for {item['item_name']}")
                        
                        if search_results and len(search_results) > 0:
                            # Handle different result structures that might come from search function
                            first_result = search_results[0]
                            logger.info(f"First result keys: {list(first_result.keys())}")
                            
                            # If price is directly in the result
                            if "price" in first_result:
                                item["price"] = first_result["price"]
                                logger.info(f"Using 'price' field: {item['price']}")
                            # If price is in item_price
                            elif "item_price" in first_result:
                                item["price"] = first_result["item_price"]
                                logger.info(f"Using 'item_price' field: {item['price']}")
                            # If price is in a nested 'prices' list (for cross-chain products)
                            elif "prices" in first_result and isinstance(first_result["prices"], list) and len(first_result["prices"]) > 0:
                                first_price = first_result["prices"][0]
                                item["price"] = first_price.get("price", None)
                                logger.info(f"Using nested 'prices' field: {item['price']}")
                            else:
                                logger.warning(f"No price found in result for {item['item_name']}")
                                item["price"] = None
                        else:
                            logger.warning(f"No search results found for {item['item_name']}")
                            item["price"] = None
                    except Exception as e:
                        logger.error(f"Error retrieving price for {item['item_name']}: {str(e)}")
                        item["price"] = None
                else:
                    logger.info(f"No city specified, skipping price lookup for {item['item_name']}")
                    item["price"] = None
                
                items.append(item)
            
            cart_data = {
                "cart_name": cart_name,
                "city": cart_city,
                "items": items
            }
            carts.append(cart_data)
            logger.info(f"Added cart {cart_name} to response")
        
        return {"email": email, "saved_carts": carts}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")