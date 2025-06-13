#!/usr/bin/env python3
"""Create Oracle tables in the correct order"""

import os
import sys

# Load environment variables
if os.path.exists('.env.oracle'):
    with open('.env.oracle', 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                try:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
                except ValueError:
                    continue

# Set Oracle mode
os.environ['USE_ORACLE'] = 'true'

from database.connection import engine
from database.models import Base, User, Cart, CartItem, Store, Price
from sqlalchemy import text

print("Creating Oracle tables...")

try:
    # Drop existing tables if needed (be careful with this in production!)
    with engine.connect() as conn:
        # Check if tables exist
        result = conn.execute(text(
            "SELECT table_name FROM user_tables WHERE table_name IN ('CART_ITEMS', 'PRICES', 'CARTS', 'STORES', 'USERS')"
        ))
        existing_tables = [row[0] for row in result]
        
        if existing_tables:
            print(f"Found existing tables: {existing_tables}")
            response = input("Drop existing tables? (yes/no): ")
            
            if response.lower() == 'yes':
                # Drop in reverse order of dependencies
                for table in ['CART_ITEMS', 'PRICES', 'CARTS', 'STORES', 'USERS']:
                    if table in existing_tables:
                        conn.execute(text(f"DROP TABLE {table} CASCADE CONSTRAINTS"))
                        print(f"Dropped table: {table}")
                conn.commit()
    
    # Create tables in correct order
    print("\nCreating tables...")
    
    # 1. Create User table first (no dependencies)
    User.__table__.create(bind=engine, checkfirst=True)
    print("✅ Created users table")
    
    # 2. Create Store table (no dependencies)
    Store.__table__.create(bind=engine, checkfirst=True)
    print("✅ Created stores table")
    
    # 3. Create Cart table (depends on User)
    Cart.__table__.create(bind=engine, checkfirst=True)
    print("✅ Created carts table")
    
    # 4. Create CartItem table (depends on Cart)
    CartItem.__table__.create(bind=engine, checkfirst=True)
    print("✅ Created cart_items table")
    
    # 5. Create Price table (depends on Store)
    Price.__table__.create(bind=engine, checkfirst=True)
    print("✅ Created prices table")
    
    # Verify all tables were created
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT table_name FROM user_tables WHERE table_name IN ('USERS', 'STORES', 'CARTS', 'CART_ITEMS', 'PRICES') ORDER BY table_name"
        ))
        created_tables = [row[0] for row in result]
        print(f"\n✅ Successfully created tables: {created_tables}")
        
        # Create a test user
        conn.execute(text(
            "INSERT INTO users (id, email, password, created_at) VALUES (1, 'test@example.com', 'hashed_password', SYSTIMESTAMP)"
        ))
        conn.commit()
        print("✅ Created test user")
        
        # Verify
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        print(f"✅ Users table has {count} record(s)")
    
    print("\n🎉 Oracle database is ready!")
    print("\nNow you can run the server with:")
    print("  export $(cat .env.oracle | grep -v '^#' | xargs)")
    print("  export TNS_ADMIN=./wallet")
    print("  python -m uvicorn api_server:app --host 0.0.0.0 --reload")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
