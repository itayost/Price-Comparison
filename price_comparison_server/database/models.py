from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    carts = relationship("Cart", back_populates="user", cascade="all, delete-orphan")

class Cart(Base):
    __tablename__ = 'carts'
    
    id = Column(Integer, primary_key=True)
    cart_name = Column(String(255), nullable=False)
    email = Column(String(255), ForeignKey('users.email'), nullable=False)
    city = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="carts")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

class CartItem(Base):
    __tablename__ = 'cart_items'
    
    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey('carts.id'), nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    cart = relationship("Cart", back_populates="items")

class Store(Base):
    __tablename__ = 'stores'
    
    id = Column(Integer, primary_key=True)
    snif_key = Column(String(50), unique=True, nullable=False, index=True)
    chain = Column(String(50), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    store_name = Column(String(255))
    
    prices = relationship("Price", back_populates="store")

class Price(Base):
    __tablename__ = 'prices'
    
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False)
    item_code = Column(String(50), index=True)
    # Reduced from 500 to 255 to avoid Oracle CLOB issues
    item_name = Column(String(255), nullable=False)  # Removed index here
    item_price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="prices")

    # Only create indexes that Oracle can handle
    __table_args__ = (
        Index('idx_store_item_code', 'store_id', 'item_code'),
        # Removed the composite index on item_name to avoid Oracle LOB issues
        # If you need to search by item_name, consider:
        # 1. Using Oracle Text indexes (requires additional setup)
        # 2. Creating a separate search column with first 255 chars
        # 3. Using full-text search capabilities
    )
