#!/usr/bin/env python3
# price_comparison_server/scripts/setup_auth.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import engine, get_db
from database.new_models import Base, User, SavedCart
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_auth_tables():
    """Create user and saved cart tables"""
    logger.info("Creating authentication tables...")
    
    try:
        # Create only the user-related tables
        User.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created users table")
        
        SavedCart.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created saved_carts table")
        
        # Verify tables exist
        with get_db() as db:
            user_count = db.query(User).count()
            cart_count = db.query(SavedCart).count()
            
            logger.info(f"\nTable verification:")
            logger.info(f"  Users table: {user_count} users")
            logger.info(f"  SavedCart table: {cart_count} carts")
            
        logger.info("\n✅ Authentication tables created successfully!")
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise


def create_test_user():
    """Create a test user for development"""
    logger.info("\nCreating test user...")
    
    from services.auth_service import AuthService
    
    with get_db() as db:
        auth_service = AuthService(db)
        
        try:
            # Create test user
            test_email = "test@example.com"
            test_password = "password123"
            
            user = auth_service.create_user(test_email, test_password)
            logger.info(f"✓ Created test user: {test_email}")
            logger.info(f"  User ID: {user.user_id}")
            logger.info(f"  Password: {test_password}")
            
        except ValueError as e:
            if "already exists" in str(e):
                logger.info(f"  Test user already exists")
            else:
                raise


def add_secret_key_to_env():
    """Add SECRET_KEY to .env if not present"""
    env_file = Path(__file__).parent.parent / '.env'
    
    if env_file.exists():
        content = env_file.read_text()
        if 'SECRET_KEY' not in content:
            import secrets
            secret_key = secrets.token_urlsafe(32)
            
            with open(env_file, 'a') as f:
                f.write(f"\n# JWT Secret Key\n")
                f.write(f"SECRET_KEY={secret_key}\n")
            
            logger.info("✓ Added SECRET_KEY to .env file")
        else:
            logger.info("✓ SECRET_KEY already in .env file")
    else:
        logger.warning("⚠️  No .env file found. Create one and add: SECRET_KEY=your-secret-key")


if __name__ == "__main__":
    logger.info("Setting up authentication...\n")
    
    # Add secret key
    add_secret_key_to_env()
    
    # Create tables
    create_auth_tables()
    
    # Create test user
    create_test_user()
    
    logger.info("\n🎉 Authentication setup complete!")
    logger.info("\nYou can now:")
    logger.info("1. Register users: POST /api/auth/register")
    logger.info("2. Login: POST /api/auth/login")
    logger.info("3. Get user info: GET /api/auth/me")
    logger.info("\nTest credentials:")
    logger.info("  Email: test@example.com")
    logger.info("  Password: password123")
