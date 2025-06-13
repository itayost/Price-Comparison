#!/usr/bin/env python3
"""Check and fix Oracle table constraints"""

import os
import sys
from sqlalchemy import text

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

print("Checking Oracle table structure...")

try:
    with engine.connect() as conn:
        # Check the users table structure
        result = conn.execute(text("""
            SELECT column_name, data_type, nullable
            FROM user_tab_columns
            WHERE table_name = 'USERS'
            ORDER BY column_id
        """))
        
        print("\nUSERS table columns:")
        for row in result:
            print(f"  - {row[0]}: {row[1]} (Nullable: {row[2]})")
        
        # Check constraints on users table
        result = conn.execute(text("""
            SELECT constraint_name, constraint_type, search_condition
            FROM user_constraints
            WHERE table_name = 'USERS'
        """))
        
        print("\nUSERS table constraints:")
        for row in result:
            print(f"  - {row[0]}: {row[1]} - {row[2] if row[2] else 'PRIMARY/UNIQUE'}")
        
        # Check if email has a unique constraint
        result = conn.execute(text("""
            SELECT constraint_name
            FROM user_constraints
            WHERE table_name = 'USERS' 
            AND constraint_type = 'U'
            AND constraint_name IN (
                SELECT constraint_name
                FROM user_cons_columns
                WHERE table_name = 'USERS'
                AND column_name = 'EMAIL'
            )
        """))
        
        email_constraint = result.fetchone()
        
        if not email_constraint:
            print("\n❌ Email column does not have a unique constraint!")
            print("Adding unique constraint...")
            
            # Add unique constraint to email
            conn.execute(text("ALTER TABLE users ADD CONSTRAINT users_email_unique UNIQUE (email)"))
            conn.commit()
            print("✅ Added unique constraint to email column")
        else:
            print(f"\n✅ Email already has unique constraint: {email_constraint[0]}")
        
        # Now try to create the remaining tables
        print("\nCreating remaining tables...")
        
        from database.models import Cart, CartItem, Price
        
        # Create Cart table
        Cart.__table__.create(bind=engine, checkfirst=True)
        print("✅ Created carts table")
        
        # Create CartItem table
        CartItem.__table__.create(bind=engine, checkfirst=True)
        print("✅ Created cart_items table")
        
        # Create Price table
        Price.__table__.create(bind=engine, checkfirst=True)
        print("✅ Created prices table")
        
        # Verify all tables
        result = conn.execute(text("""
            SELECT table_name 
            FROM user_tables 
            WHERE table_name IN ('USERS', 'STORES', 'CARTS', 'CART_ITEMS', 'PRICES')
            ORDER BY table_name
        """))
        
        tables = [row[0] for row in result]
        print(f"\n✅ All tables created: {tables}")
        
        # Create test data
        print("\nCreating test data...")
        
        # Check if test user exists
        result = conn.execute(text("SELECT COUNT(*) FROM users WHERE email = 'test@example.com'"))
        if result.scalar() == 0:
            conn.execute(text("""
                INSERT INTO users (id, email, password, created_at) 
                VALUES (1, 'test@example.com', 'hashed_password', SYSTIMESTAMP)
            """))
            conn.commit()
            print("✅ Created test user")
        else:
            print("✅ Test user already exists")
        
        print("\n🎉 Oracle database is ready!")
        print("\nYou can now run the server!")
        
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
