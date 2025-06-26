# price_comparison_server/database/new_models.py

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, 
    UniqueConstraint, Index, Boolean, Text, Numeric, Sequence, CLOB
)
from sqlalchemy.types import Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship
from datetime import datetime
import os
import json

class Base(DeclarativeBase):
    pass

# Check if we're using Oracle
USE_ORACLE = os.getenv("USE_ORACLE", "false").lower() == "true"

class Chain(Base):
    """Master table for supermarket chains"""
    __tablename__ = 'chains'

    if USE_ORACLE:
        chain_id = Column(Integer, Sequence('chain_id_seq'), primary_key=True)
    else:
        chain_id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(50), unique=True, nullable=False)  # 'shufersal', 'victory'
    display_name = Column(String(100))  # 'שופרסל', 'ויקטורי'

    # Relationships
    branches = relationship("Branch", back_populates="chain", cascade="all, delete-orphan")
    chain_products = relationship("ChainProduct", back_populates="chain", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Chain(name='{self.name}')>"


class Branch(Base):
    """Store branches/locations"""
    __tablename__ = 'branches'

    if USE_ORACLE:
        branch_id = Column(Integer, Sequence('branch_id_seq'), primary_key=True)
    else:
        branch_id = Column(Integer, primary_key=True, autoincrement=True)

    chain_id = Column(Integer, ForeignKey('chains.chain_id'), nullable=False)
    store_id = Column(String(50), nullable=False)  # Original store ID from chain
    name = Column(String(255))
    address = Column(String(500))
    city = Column(String(100), nullable=False)

    # Relationships
    chain = relationship("Chain", back_populates="branches")
    prices = relationship("BranchPrice", back_populates="branch", cascade="all, delete-orphan")

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('chain_id', 'store_id', name='uq_chain_store'),
        Index('idx_chain_city', 'chain_id', 'city'),
    )

    def __repr__(self):
        return f"<Branch(chain_id={self.chain_id}, store_id='{self.store_id}', city='{self.city}')>"


class ChainProduct(Base):
    """Chain-specific products with their barcodes"""
    __tablename__ = 'chain_products'

    if USE_ORACLE:
        chain_product_id = Column(Integer, Sequence('chain_product_id_seq'), primary_key=True)
    else:
        chain_product_id = Column(Integer, primary_key=True, autoincrement=True)

    chain_id = Column(Integer, ForeignKey('chains.chain_id'), nullable=False)
    barcode = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)  # Original name from chain

    # Relationships
    chain = relationship("Chain", back_populates="chain_products")
    prices = relationship("BranchPrice", back_populates="chain_product", cascade="all, delete-orphan")

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('chain_id', 'barcode', name='uq_chain_barcode'),
        Index('idx_name', 'name'),
    )

    def __repr__(self):
        return f"<ChainProduct(chain_id={self.chain_id}, barcode='{self.barcode}', name='{self.name}')>"


class BranchPrice(Base):
    """Current prices at each branch"""
    __tablename__ = 'branch_prices'

    if USE_ORACLE:
        price_id = Column(Integer, Sequence('price_id_seq'), primary_key=True)
    else:
        price_id = Column(Integer, primary_key=True, autoincrement=True)

    chain_product_id = Column(Integer, ForeignKey('chain_products.chain_product_id'), nullable=False)
    branch_id = Column(Integer, ForeignKey('branches.branch_id'), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    chain_product = relationship("ChainProduct", back_populates="prices")
    branch = relationship("Branch", back_populates="prices")

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('chain_product_id', 'branch_id', name='uq_product_branch'),
        Index('idx_branch', 'branch_id'),
        Index('idx_updated', 'last_updated'),
    )

    def __repr__(self):
        return f"<BranchPrice(chain_product_id={self.chain_product_id}, branch_id={self.branch_id}, price={self.price})>"


# Optional: History table for price tracking
class PriceHistory(Base):
    """Historical price data (optional - for tracking price changes)"""
    __tablename__ = 'price_history'

    if USE_ORACLE:
        history_id = Column(Integer, Sequence('history_id_seq'), primary_key=True)
    else:
        history_id = Column(Integer, primary_key=True, autoincrement=True)

    chain_product_id = Column(Integer, ForeignKey('chain_products.chain_product_id'), nullable=False)
    branch_id = Column(Integer, ForeignKey('branches.branch_id'), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_history_product_branch', 'chain_product_id', 'branch_id'),
        Index('idx_history_date', 'recorded_at'),
    )


class User(Base):
    """Users table for authentication"""
    __tablename__ = 'users'

    if USE_ORACLE:
        user_id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    else:
        user_id = Column(Integer, primary_key=True, autoincrement=True)

    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    saved_carts = relationship("SavedCart", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(email='{self.email}')>"


class SavedCart(Base):
    """Saved shopping carts for users"""
    __tablename__ = 'saved_carts'

    if USE_ORACLE:
        cart_id = Column(Integer, Sequence('cart_id_seq'), primary_key=True)
    else:
        cart_id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    cart_name = Column(String(100), nullable=False)
    city = Column(String(100))

    # Store JSON as text - Oracle doesn't support JSON type in older versions
    items = Column(Text)  # Will store JSON as text

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="saved_carts")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'cart_name', name='uq_user_cart_name'),
        Index('idx_saved_cart_user', 'user_id'),
    )

    def __repr__(self):
        return f"<SavedCart(user_id={self.user_id}, cart_name='{self.cart_name}')>"

    # Helper methods for JSON handling
    @property
    def items_list(self):
        """Get items as Python list"""
        if self.items:
            return json.loads(self.items)
        return []

    @items_list.setter
    def items_list(self, value):
        """Set items from Python list"""
        self.items = json.dumps(value)


# Helper functions for creating the schema
def create_all_tables(engine):
    """Create all tables in the database"""
    if USE_ORACLE:
        # Create sequences first for Oracle
        from sqlalchemy import text
        sequences = [
            'chain_id_seq', 'branch_id_seq',
            'chain_product_id_seq', 'price_id_seq', 'history_id_seq',
            'user_id_seq', 'cart_id_seq'
        ]

        with engine.begin() as conn:
            for seq in sequences:
                try:
                    conn.execute(text(f"CREATE SEQUENCE {seq}"))
                    print(f"Created sequence: {seq}")
                except Exception as e:
                    if "ORA-00955" not in str(e):  # Sequence already exists
                        print(f"Warning creating sequence {seq}: {e}")

    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully!")


def drop_all_tables(engine):
    """Drop all tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)
    print("⚠️ All tables dropped!")


# Initial data seeding function
def seed_initial_data(session):
    """Seed initial chain data"""
    chains = [
        Chain(name='shufersal', display_name='שופרסל'),
        Chain(name='victory', display_name='ויקטורי')
    ]

    for chain in chains:
        existing = session.query(Chain).filter_by(name=chain.name).first()
        if not existing:
            session.add(chain)

    session.commit()
    print("✅ Initial chain data seeded!")
