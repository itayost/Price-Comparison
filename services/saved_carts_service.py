# price_comparison_server/services/saved_carts_service.py

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import json  # Use standard json for serialization
import logging

from database.new_models import User, SavedCart
from services.cart_service import CartItem, CartComparisonService

logger = logging.getLogger(__name__)


class SavedCartsService:
    """Service for managing saved shopping carts with Text column"""

    def __init__(self, db: Session):
        self.db = db

    def save_cart(self, user_id: int, cart_name: str, city: str,
                  items: List[CartItem]) -> SavedCart:
        """Save a shopping cart for a user"""

        # Check if cart with same name exists for user
        existing = self.db.query(SavedCart).filter(
            and_(
                SavedCart.user_id == user_id,
                SavedCart.cart_name == cart_name
            )
        ).first()

        # Prepare items data for JSON storage
        items_data = [
            {
                'barcode': item.barcode,
                'quantity': item.quantity,
                'name': item.name
            }
            for item in items
        ]

        # Convert to JSON string for Text column
        items_json = json.dumps(items_data, ensure_ascii=False)

        if existing:
            # Update existing cart
            existing.city = city
            existing.items = items_json  # Store as JSON string
            existing.updated_at = datetime.utcnow()
            saved_cart = existing
            logger.info(f"Updated cart '{cart_name}' for user {user_id}")
        else:
            # Create new cart
            saved_cart = SavedCart(
                user_id=user_id,
                cart_name=cart_name,
                city=city,
                items=items_json,  # Store as JSON string
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.db.add(saved_cart)
            logger.info(f"Created new cart '{cart_name}' for user {user_id}")

        self.db.commit()
        return saved_cart

    def _parse_items(self, items_json: str) -> List[Dict[str, Any]]:
        """Parse items from JSON string"""
        try:
            return json.loads(items_json) if items_json else []
        except:
            return []

    def get_user_carts(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all saved carts for a user"""
        carts = self.db.query(SavedCart).filter(
            SavedCart.user_id == user_id
        ).order_by(SavedCart.updated_at.desc()).all()

        result = []
        for cart in carts:
            items = self._parse_items(cart.items)
            result.append({
                'cart_id': cart.cart_id,
                'cart_name': cart.cart_name,
                'city': cart.city,
                'item_count': len(items),
                'created_at': cart.created_at.isoformat(),
                'updated_at': cart.updated_at.isoformat()
            })

        return result

    def get_cart_by_id(self, user_id: int, cart_id: int) -> Optional[SavedCart]:
        """Get a specific cart by ID"""
        return self.db.query(SavedCart).filter(
            and_(
                SavedCart.cart_id == cart_id,
                SavedCart.user_id == user_id
            )
        ).first()

    def load_and_compare_cart(self, user_id: int, cart_id: int) -> Dict[str, Any]:
        """Load a saved cart and get current prices"""
        # Get the saved cart
        saved_cart = self.get_cart_by_id(user_id, cart_id)
        if not saved_cart:
            return None

        # Parse items from JSON string
        items_data = self._parse_items(saved_cart.items)

        # Convert to CartItem objects
        cart_items = [
            CartItem(
                barcode=item['barcode'],
                quantity=item['quantity'],
                name=item.get('name')
            )
            for item in items_data
        ]

        # Run price comparison with current prices
        comparison_service = CartComparisonService(self.db)
        comparison = comparison_service.compare_cart(cart_items, saved_cart.city)

        # Return cart info with current prices
        return {
            'cart_info': {
                'cart_id': saved_cart.cart_id,
                'cart_name': saved_cart.cart_name,
                'city': saved_cart.city,
                'created_at': saved_cart.created_at.isoformat(),
                'updated_at': saved_cart.updated_at.isoformat()
            },
            'items': items_data,
            'comparison': {
                'total_items': comparison.total_items,
                'cheapest_store': {
                    'branch_name': comparison.cheapest_store.branch_name,
                    'chain_name': comparison.cheapest_store.chain_display_name,
                    'total_price': comparison.cheapest_store.total_price,
                    'available_items': comparison.cheapest_store.available_items,
                    'missing_items': comparison.cheapest_store.missing_items
                } if comparison.cheapest_store else None,
                'comparison_time': comparison.comparison_time.isoformat()
            }
        }

    def delete_cart(self, user_id: int, cart_id: int) -> bool:
        """Delete a saved cart"""
        cart = self.get_cart_by_id(user_id, cart_id)
        if not cart:
            return False

        self.db.delete(cart)
        self.db.commit()
        logger.info(f"Deleted cart {cart_id} for user {user_id}")
        return True

    def update_cart_items(self, user_id: int, cart_id: int,
                          items: List[CartItem]) -> Optional[SavedCart]:
        """Update items in an existing cart"""
        cart = self.get_cart_by_id(user_id, cart_id)
        if not cart:
            return None

        # Prepare items data for JSON storage
        items_data = [
            {
                'barcode': item.barcode,
                'quantity': item.quantity,
                'name': item.name
            }
            for item in items
        ]

        # Update cart
        cart.items = json.dumps(items_data, ensure_ascii=False)
        cart.updated_at = datetime.utcnow()

        self.db.commit()
        logger.info(f"Updated items in cart {cart_id} for user {user_id}")
        return cart
