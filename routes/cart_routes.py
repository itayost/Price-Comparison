# price_comparison_server/routes/cart_routes.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging
from database.connection import get_db_session
from services.cart_service import CartComparisonService, CartItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cart", tags=["cart"])


# Pydantic models for API
class CartItemRequest(BaseModel):
    barcode: str = Field(..., description="Product barcode")
    quantity: int = Field(1, ge=1, description="Quantity (must be positive)")
    name: Optional[str] = Field(None, description="Optional product name")


class CartCompareRequest(BaseModel):
    city: str = Field(..., description="City name (Hebrew or English)")
    items: List[CartItemRequest] = Field(..., description="List of items in cart")


class StoreResult(BaseModel):
    branch_id: int
    branch_name: str
    branch_address: str
    city: str
    chain_name: str
    chain_display_name: str
    available_items: int
    missing_items: int
    total_price: float
    items_detail: List[Dict[str, Any]]


class CartComparisonResponse(BaseModel):
    success: bool
    total_items: int
    city: str
    cheapest_store: Optional[StoreResult]
    all_stores: List[StoreResult]
    comparison_time: str


@router.post("/compare", response_model=CartComparisonResponse)
def compare_cart_prices(request: CartCompareRequest, db: Session = Depends(get_db_session)):
    """
    Compare cart prices across all stores in a city.

    Returns the cheapest store and price breakdown for all stores.
    """
    try:
        # Convert request items to CartItem objects
        cart_items = [
            CartItem(
                barcode=item.barcode,
                quantity=item.quantity,
                name=item.name
            )
            for item in request.items
        ]

        # Get comparison service
        service = CartComparisonService(db)

        # Compare prices
        comparison = service.compare_cart(cart_items, request.city)

        # Convert to response format
        response = CartComparisonResponse(
            success=True,
            total_items=comparison.total_items,
            city=comparison.city,
            cheapest_store=StoreResult(
                branch_id=comparison.cheapest_store.branch_id,
                branch_name=comparison.cheapest_store.branch_name,
                branch_address=comparison.cheapest_store.branch_address,
                city=comparison.cheapest_store.city,
                chain_name=comparison.cheapest_store.chain_name,
                chain_display_name=comparison.cheapest_store.chain_display_name,
                available_items=comparison.cheapest_store.available_items,
                missing_items=comparison.cheapest_store.missing_items,
                total_price=comparison.cheapest_store.total_price,
                items_detail=comparison.cheapest_store.items_detail
            ) if comparison.cheapest_store else None,
            all_stores=[
                StoreResult(
                    branch_id=store.branch_id,
                    branch_name=store.branch_name,
                    branch_address=store.branch_address,
                    city=store.city,
                    chain_name=store.chain_name,
                    chain_display_name=store.chain_display_name,
                    available_items=store.available_items,
                    missing_items=store.missing_items,
                    total_price=store.total_price,
                    items_detail=store.items_detail
                )
                for store in comparison.all_stores
            ],
            comparison_time=comparison.comparison_time.isoformat()
        )

        return response

    except Exception as e:
        logger.error(f"Error comparing cart: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to compare cart: {str(e)}")


@router.get("/product/{barcode}")
def get_product_info(barcode: str, db: Session = Depends(get_db_session)):
    """Get product information including price range across all stores"""
    try:
        service = CartComparisonService(db)
        product_info = service.get_product_info(barcode)

        if not product_info:
            raise HTTPException(status_code=404, detail=f"Product with barcode {barcode} not found")

        return {
            "success": True,
            "product": product_info
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get product information")


@router.get("/search")
def search_products(query: str, limit: int = 20, db: Session = Depends(get_db_session)):
    """Search for products by name or barcode"""
    try:
        if len(query) < 2:
            raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")

        service = CartComparisonService(db)
        results = service.search_products(query, limit)

        return {
            "success": True,
            "query": query,
            "count": len(results),
            "products": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching products: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search products")


# Sample cart for testing
@router.get("/sample")
def get_sample_cart():
    """Get a sample cart for testing"""
    return {
        "city": "תל אביב",
        "items": [
            {
                "barcode": "7290000000001",
                "quantity": 2,
                "name": "חלב 3%"
            },
            {
                "barcode": "7290000000002",
                "quantity": 1,
                "name": "לחם אחיד"
            },
            {
                "barcode": "7290000000003",
                "quantity": 3,
                "name": "ביצים L"
            }
        ]
    }
