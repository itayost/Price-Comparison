from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.data_models import SaveCartRequest
from database.connection import get_db_session
from database.models import User, Cart, CartItem
from services.search_service import search_products_by_name_and_city

router = APIRouter(tags=["carts"])

@router.post("/save-cart")
def save_cart(request: SaveCartRequest, db: Session = Depends(get_db_session)):
    try:
        # Check if user exists
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if cart with same name exists
        existing_cart = db.query(Cart).filter(
            Cart.email == request.email,
            Cart.cart_name == request.cart_name
        ).first()

        if existing_cart:
            # Delete existing cart and items
            db.query(CartItem).filter(CartItem.cart_id == existing_cart.id).delete()
            db.delete(existing_cart)

        # Create new cart
        new_cart = Cart(
            email=request.email,
            cart_name=request.cart_name,
            city=request.city
        )
        db.add(new_cart)
        db.flush()  # Get the cart ID

        # Add cart items
        for item in request.items:
            cart_item = CartItem(
                cart_id=new_cart.id,
                item_name=item.item_name,
                quantity=item.quantity
            )
            db.add(cart_item)

        db.commit()
        return {"message": "Cart saved successfully"}

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving cart: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/savedcarts/{email}")
def get_saved_carts(email: str, city: str = None, db: Session = Depends(get_db_session)):
    try:
        logger.info(f"Getting saved carts for email: {email}, city: {city}")

        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.warning(f"User not found: {email}")
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's carts
        query = db.query(Cart).filter(Cart.email == email)
        if city:
            query = query.filter(Cart.city == city)

        carts = query.all()
        logger.info(f"Found {len(carts)} carts")

        result = []
        for cart in carts:
            cart_data = {
                "cart_name": cart.cart_name,
                "city": cart.city,
                "items": []
            }

            # Get cart items
            for cart_item in cart.items:
                item_data = {
                    "item_name": cart_item.item_name,
                    "quantity": cart_item.quantity,
                    "price": None
                }

                # Try to get current price
                if cart.city:
                    try:
                        search_results = search_products_by_name_and_city(
                            cart.city,
                            cart_item.item_name
                        )
                        if search_results:
                            # Get price from first result
                            first_result = search_results[0]
                            if "price" in first_result:
                                item_data["price"] = first_result["price"]
                            elif "prices" in first_result and first_result["prices"]:
                                item_data["price"] = first_result["prices"][0].get("price")
                    except Exception as e:
                        logger.error(f"Error getting price for {cart_item.item_name}: {str(e)}")

                cart_data["items"].append(item_data)

            result.append(cart_data)

        return {"email": email, "saved_carts": result}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting saved carts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
