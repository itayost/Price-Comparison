# price_comparison_server/routes/saved_carts_routes.py

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging

from database.connection import SessionLocal
from services.saved_carts_service import SavedCartsService
from services.cart_service import CartItem
from routes.auth_routes import get_current_user
from database.new_models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/saved-carts", tags=["saved-carts"])


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic models
class SaveCartRequest(BaseModel):
    cart_name: str = Field(..., min_length=1, max_length=100, description="Name for the cart")
    city: str = Field(..., description="City for price comparison")
    items: List[Dict[str, Any]] = Field(..., description="List of items with barcode, quantity, and optional name")


class UpdateCartItemsRequest(BaseModel):
    items: List[Dict[str, Any]] = Field(..., description="Updated list of items")


class CartListResponse(BaseModel):
    cart_id: int
    cart_name: str
    city: str
    item_count: int
    created_at: str
    updated_at: str


class SavedCartResponse(BaseModel):
    success: bool
    cart_id: int
    message: str


@router.post("/save", response_model=SavedCartResponse)
def save_cart(
    request: SaveCartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save a shopping cart for the current user.
    If a cart with the same name exists, it will be updated.
    """
    try:
        service = SavedCartsService(db)

        # Convert items to CartItem objects
        cart_items = [
            CartItem(
                barcode=item['barcode'],
                quantity=item.get('quantity', 1),
                name=item.get('name')
            )
            for item in request.items
        ]

        # Save the cart
        saved_cart = service.save_cart(
            user_id=current_user.user_id,
            cart_name=request.cart_name,
            city=request.city,
            items=cart_items
        )

        return SavedCartResponse(
            success=True,
            cart_id=saved_cart.cart_id,
            message=f"Cart '{request.cart_name}' saved successfully"
        )

    except Exception as e:
        logger.error(f"Error saving cart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save cart: {str(e)}"
        )


@router.get("/list", response_model=List[CartListResponse])
def list_user_carts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all saved carts for the current user"""
    try:
        service = SavedCartsService(db)
        carts = service.get_user_carts(current_user.user_id)

        return [
            CartListResponse(
                cart_id=cart['cart_id'],
                cart_name=cart['cart_name'],
                city=cart['city'],
                item_count=cart['item_count'],
                created_at=cart['created_at'],
                updated_at=cart['updated_at']
            )
            for cart in carts
        ]

    except Exception as e:
        logger.error(f"Error listing carts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve carts"
        )


@router.get("/{cart_id}")
def get_cart_details(
    cart_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a saved cart"""
    try:
        service = SavedCartsService(db)
        cart = service.get_cart_by_id(current_user.user_id, cart_id)

        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )

        # Parse items from JSON string if needed
        items = cart.items
        if isinstance(items, str):
            import json
            items = json.loads(items)

        return {
            "success": True,
            "cart": {
                "cart_id": cart.cart_id,
                "cart_name": cart.cart_name,
                "city": cart.city,
                "items": items,
                "created_at": cart.created_at.isoformat(),
                "updated_at": cart.updated_at.isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cart details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cart details"
        )


@router.get("/{cart_id}/compare")
def compare_saved_cart(
    cart_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Load a saved cart and get current price comparison"""
    try:
        service = SavedCartsService(db)
        result = service.load_and_compare_cart(current_user.user_id, cart_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )

        return {
            "success": True,
            "cart_info": result['cart_info'],
            "items": result['items'],
            "comparison": result['comparison']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing saved cart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare cart prices"
        )


@router.delete("/{cart_id}")
def delete_cart(
    cart_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a saved cart"""
    try:
        service = SavedCartsService(db)
        deleted = service.delete_cart(current_user.user_id, cart_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )

        return {
            "success": True,
            "message": "Cart deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting cart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete cart"
        )
