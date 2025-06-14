from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Index, Sequence, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    # Oracle needs sequences for auto-increment
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    email = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    carts = relationship("Cart", back_populates="user", cascade="all, delete-orphan")

    # Explicitly define unique constraint for Oracle
    __table_args__ = (
        UniqueConstraint('email', name='uk_users_email'),
        # No need for separate index - unique constraint creates one automatically
    )

class Cart(Base):
    __tablename__ = 'carts'

    id = Column(Integer, Sequence('cart_id_seq'), primary_key=True)
    cart_name = Column(String(255), nullable=False)
    email = Column(String(255), ForeignKey('users.email'), nullable=False)
    city = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="carts", foreign_keys=[email])
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    # Add index for email lookups
    __table_args__ = (
        Index('idx_cart_email', 'email'),
    )

class CartItem(Base):
    __tablename__ = 'cart_items'

    id = Column(Integer, Sequence('cart_item_id_seq'), primary_key=True)
    cart_id = Column(Integer, ForeignKey('carts.id'), nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)

    cart = relationship("Cart", back_populates="items")

class Store(Base):
    __tablename__ = 'stores'

    id = Column(Integer, Sequence('store_id_seq'), primary_key=True)
    snif_key = Column(String(50), unique=True, nullable=False, index=True)
    chain = Column(String(50), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    store_name = Column(String(255))

    prices = relationship("Price", back_populates="store", cascade="all, delete-orphan")

    # Add composite index for chain+city lookups
    __table_args__ = (
        Index('idx_store_chain_city', 'chain', 'city'),
    )

class Price(Base):
    __tablename__ = 'prices'

    id = Column(Integer, Sequence('price_id_seq'), primary_key=True)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False)
    item_code = Column(String(50), index=True)
    # Keep item_name reasonable length for Oracle
    item_name = Column(String(255), nullable=False)
    item_price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="prices")

    # Oracle-friendly indexes
    __table_args__ = (
        # Index for store+item lookups
        Index('idx_price_store_item', 'store_id', 'item_code'),
        # Single column index for item name searches
        # Note: For full-text search, consider Oracle Text indexes
        Index('idx_price_item_name', 'item_name'),
    )

# For development: function to create sample data
def create_sample_data(db_session):
    """Create some sample data for testing"""
    try:
        # Create a test user
        test_user = User(email="test@example.com", password="hashed_password_here")
        db_session.add(test_user)
        db_session.flush()

        # Create a test store
        test_store = Store(
            snif_key="7290027600007-001-001",
            chain="shufersal",
            city="Tel Aviv",
            store_name="Shufersal Test Store"
        )
        db_session.add(test_store)
        db_session.flush()

        # Create some test prices
        test_items = [
            ("7290000000001", "חלב 3%", 6.9),
            ("7290000000002", "לחם אחיד", 5.5),
            ("7290000000003", "ביצים L", 12.9),
        ]

        for code, name, price in test_items:
            price_obj = Price(
                store_id=test_store.id,
                item_code=code,
                item_name=name,
                item_price=price
            )
            db_session.add(price_obj)

        db_session.commit()
        print("✅ Sample data created successfully")

    except Exception as e:
        db_session.rollback()
        print(f"❌ Error creating sample data: {str(e)}")
