#!/usr/bin/env python3
"""Test Oracle database connection"""

import os
import sys

# Load environment variables from .env.oracle
if os.path.exists('.env.oracle'):
    with open('.env.oracle', 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Set USE_ORACLE before importing
os.environ['USE_ORACLE'] = 'true'

from database.connection import engine, init_db
from database.models import User, Store, Price
from sqlalchemy import text

def test_oracle():
    try:
        print("Testing Oracle connection...")
        print(f"TNS_ADMIN: {os.environ.get('TNS_ADMIN')}")
        print(f"Service: {os.environ.get('ORACLE_SERVICE')}")
        
        # Test basic connection
        with engine.connect() as conn:
            # Oracle-specific query
            result = conn.execute(text("SELECT 'Hello from Oracle' as message FROM DUAL"))
            row = result.fetchone()
            print(f"✅ Connection successful: {row[0]}")
            
            # Check Oracle version
            result = conn.execute(text("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1"))
            version = result.fetchone()
            print(f"✅ Oracle version: {version[0]}")
        
        # Initialize tables
        print("\nCreating tables...")
        init_db()
        print("✅ Tables created successfully!")
        
        # List tables
        with engine.connect() as conn:
            result = conn.execute(text(
                """SELECT table_name FROM user_tables 
                   WHERE table_name IN ('USERS', 'STORES', 'PRICES', 'CARTS', 'CART_ITEMS')
                   ORDER BY table_name"""
            ))
            tables = [row[0] for row in result]
            print(f"✅ Found tables: {tables}")
            
        # Test insert and select
        from database.connection import get_db
        with get_db() as db:
            # Check if test user exists
            test_user = db.query(User).filter(User.email == "test@example.com").first()
            if not test_user:
                # Create test user
                test_user = User(email="test@example.com", password="hashed_password")
                db.add(test_user)
                db.commit()
                print("✅ Created test user")
            else:
                print("✅ Test user already exists")
            
            # Count records
            user_count = db.query(User).count()
            print(f"✅ Users in database: {user_count}")
            
        print("\n🎉 Oracle database is working correctly!")
        return True
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set TNS_ADMIN BEFORE importing database modules
    wallet_dir = os.path.abspath(os.environ.get('ORACLE_WALLET_DIR', './wallet'))
    os.environ['TNS_ADMIN'] = wallet_dir

    print(f"Setting TNS_ADMIN to: {wallet_dir}")
    print(f"Wallet directory exists: {os.path.exists(wallet_dir)}")

    if os.path.exists(wallet_dir):
        print(f"Wallet files: {os.listdir(wallet_dir)}")

    if test_oracle():
        print("\n✅ All tests passed! Your Oracle connection is ready.")
        print("\nTo run the server with Oracle:")
        print("  ./run_oracle.sh")
        print("\nOr manually:")
        print("  export $(cat .env.oracle | grep -v '^#' | xargs)")
        print(f"  export TNS_ADMIN={wallet_dir}")
        print("  python -m uvicorn api_server:app --host 0.0.0.0 --reload")
    else:
        print("\n❌ Tests failed. Please check your configuration.")
        sys.exit(1)
