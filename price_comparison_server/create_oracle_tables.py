#!/usr/bin/env python3
"""
Oracle Table Creation Script
Creates all necessary tables for the price comparison app in Oracle
"""

import os
import sys
from sqlalchemy import create_engine, text, Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.connection import engine

Base = declarative_base()

# Define Oracle-compatible models
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Cart(Base):
    __tablename__ = 'carts'

    id = Column(Integer, primary_key=True)
    cart_name = Column(String(255), nullable=False)
    email = Column(String(255), ForeignKey('users.email'), nullable=False)
    city = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class CartItem(Base):
    __tablename__ = 'cart_items'

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey('carts.id'), nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)

class Store(Base):
    __tablename__ = 'stores'

    id = Column(Integer, primary_key=True)
    snif_key = Column(String(50), unique=True, nullable=False, index=True)
    chain = Column(String(50), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    store_name = Column(String(255))

class Price(Base):
    __tablename__ = 'prices'

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False)
    item_code = Column(String(50), index=True)
    item_name = Column(String(255), nullable=False)  # No index on this field
    item_price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_store_item_code', 'store_id', 'item_code'),
    )

def drop_all_tables():
    """Drop all tables if they exist"""
    print("Dropping existing tables...")

    with engine.connect() as conn:
        # Drop tables in reverse order of dependencies
        tables = ['prices', 'stores', 'cart_items', 'carts', 'users']

        for table in tables:
            try:
                conn.execute(text(f"DROP TABLE {table} CASCADE CONSTRAINTS"))
                conn.commit()
                print(f"✅ Dropped table: {table}")
            except Exception as e:
                if "ORA-00942" not in str(e):  # Table doesn't exist
                    print(f"⚠️  Could not drop {table}: {str(e)}")
                conn.rollback()

def create_sequences():
    """Create sequences for auto-incrementing IDs in Oracle"""
    print("\nCreating sequences...")

    sequences = [
        ('users_seq', 'users'),
        ('carts_seq', 'carts'),
        ('cart_items_seq', 'cart_items'),
        ('stores_seq', 'stores'),
        ('prices_seq', 'prices')
    ]

    with engine.connect() as conn:
        for seq_name, table_name in sequences:
            try:
                # Drop sequence if exists
                conn.execute(text(f"DROP SEQUENCE {seq_name}"))
                conn.commit()
            except:
                conn.rollback()

            try:
                # Create sequence
                conn.execute(text(f"CREATE SEQUENCE {seq_name} START WITH 1 INCREMENT BY 1"))
                conn.commit()
                print(f"✅ Created sequence: {seq_name}")
            except Exception as e:
                print(f"❌ Error creating sequence {seq_name}: {str(e)}")
                conn.rollback()

def create_triggers():
    """Create triggers for auto-incrementing IDs"""
    print("\nCreating triggers...")

    triggers = [
        ('users_trigger', 'users', 'users_seq'),
        ('carts_trigger', 'carts', 'carts_seq'),
        ('cart_items_trigger', 'cart_items', 'cart_items_seq'),
        ('stores_trigger', 'stores', 'stores_seq'),
        ('prices_trigger', 'prices', 'prices_seq')
    ]

    with engine.connect() as conn:
        for trigger_name, table_name, seq_name in triggers:
            trigger_sql = f"""
            CREATE OR REPLACE TRIGGER {trigger_name}
            BEFORE INSERT ON {table_name}
            FOR EACH ROW
            BEGIN
                IF :new.id IS NULL THEN
                    SELECT {seq_name}.NEXTVAL INTO :new.id FROM dual;
                END IF;
            END;
            """

            try:
                conn.execute(text(trigger_sql))
                conn.commit()
                print(f"✅ Created trigger: {trigger_name}")
            except Exception as e:
                print(f"❌ Error creating trigger {trigger_name}: {str(e)}")
                conn.rollback()

def create_all_tables():
    """Create all tables"""
    print("\nCreating tables...")

    try:
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        raise

def verify_tables():
    """Verify all tables were created correctly"""
    print("\nVerifying tables...")

    with engine.connect() as conn:
        # Check tables exist
        tables = ['users', 'carts', 'cart_items', 'stores', 'prices']

        for table in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"✅ Table {table} exists (row count: {count})")
            except Exception as e:
                print(f"❌ Table {table} check failed: {str(e)}")

def main():
    """Main function"""
    print("Oracle Table Creation Script")
    print("=" * 50)

    # Ask for confirmation
    response = input("\nThis will DROP and RECREATE all tables. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return

    try:
        # Drop existing tables
        drop_all_tables()

        # Create sequences for auto-increment
        create_sequences()

        # Create all tables
        create_all_tables()

        # Create triggers for auto-increment
        create_triggers()

        # Verify everything was created
        verify_tables()

        print("\n✅ Oracle database setup completed successfully!")

    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
