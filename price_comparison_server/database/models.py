from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Index, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

# Check if we're using Oracle
USE_ORACLE = os.getenv("USE_ORACLE", "false").lower() == "true"

class User(Base):
    __tablename__ = 'users'

    # Oracle needs sequences for auto-increment
    if USE_ORACLE:
        id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    else:
        id = Column(Integer, primary_key=True)

    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    carts = relationship("Cart", back_populates="user", cascade="all, delete-orphan")

class Cart(Base):
    __tablename__ = 'carts'

    if USE_ORACLE:
        id = Column(Integer, Sequence('cart_id_seq'), primary_key=True)
    else:
        id = Column(Integer, primary_key=True)

    cart_name = Column(String(255), nullable=False)
    email = Column(String(255), ForeignKey('users.email'), nullable=False)
    city = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="carts")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

class CartItem(Base):
    __tablename__ = 'cart_items'

    if USE_ORACLE:
        id = Column(Integer, Sequence('cart_item_id_seq'), primary_key=True)
    else:
        id = Column(Integer, primary_key=True)

    cart_id = Column(Integer, ForeignKey('carts.id'), nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)

    cart = relationship("Cart", back_populates="items")

class Store(Base):
    __tablename__ = 'stores'

    if USE_ORACLE:
        id = Column(Integer, Sequence('store_id_seq'), primary_key=True)
    else:
        id = Column(Integer, primary_key=True)

    snif_key = Column(String(50), unique=True, nullable=False, index=True)
    chain = Column(String(50), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    store_name = Column(String(255))

    prices = relationship("Price", back_populates="store")

class Price(Base):
    __tablename__ = 'prices'

    if USE_ORACLE:
        id = Column(Integer, Sequence('price_id_seq'), primary_key=True)
        # Oracle has a 30-character limit for index names
        __table_args__ = (
            Index('idx_store_item', 'store_id', 'item_name'),
            Index('idx_item_price', 'item_name', 'item_price'),
        )
    else:
        id = Column(Integer, primary_key=True)
        __table_args__ = (
            Index('idx_store_item', 'store_id', 'item_name'),
            Index('idx_item_price', 'item_name', 'item_price'),
        )

    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False)
    item_code = Column(String(50), index=True)
    # Oracle might need CLOB for very long strings
    item_name = Column(String(500) if not USE_ORACLE else Text, nullable=False, index=True)
    item_price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="prices")
