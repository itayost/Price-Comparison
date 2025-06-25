import os
from fastapi import HTTPException
from sqlalchemy.orm import Session
from database.models import Store, Price, User, Cart, CartItem

# These constants are kept for backward compatibility
USER_DB = "users.db"  # Not used with PostgreSQL
DBS = {
    "shufersal": "shufersal_prices",  # Not used with PostgreSQL
    "victory": "victory_prices"  # Not used with PostgreSQL
}

def get_corrected_city_path(chain_dir, city_name):
    """DEPRECATED - Not needed with PostgreSQL"""
    return None

def init_user_db():
    """DEPRECATED - Tables are created by SQLAlchemy"""
    pass

def init_cart_db():
    """DEPRECATED - Tables are created by SQLAlchemy"""
    pass

def get_db_connection(db_name: str, city: str, snif_key: str):
    """DEPRECATED - Use SQLAlchemy session instead"""
    raise NotImplementedError("This function is deprecated. Use SQLAlchemy session instead.")

# New helper functions for PostgreSQL
def get_store_by_snif_key(db: Session, snif_key: str) -> Store:
    """Get a store by its snif_key"""
    store = db.query(Store).filter(Store.snif_key == snif_key).first()
    if not store:
        raise HTTPException(status_code=404, detail=f"Store {snif_key} not found")
    return store

def get_stores_by_city(db: Session, city: str, chain: str = None) -> list[Store]:
    """Get all stores in a city, optionally filtered by chain"""
    query = db.query(Store).filter(Store.city == city)
    if chain:
        query = query.filter(Store.chain == chain)
    return query.all()

def get_prices_by_store(db: Session, store_id: int, limit: int = None) -> list[Price]:
    """Get prices for a specific store"""
    query = db.query(Price).filter(Price.store_id == store_id)
    if limit:
        query = query.limit(limit)
    return query.all()
