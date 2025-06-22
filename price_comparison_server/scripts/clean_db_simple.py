#!/usr/bin/env python3
# clean_db_simple.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import engine, get_db
from sqlalchemy import text, MetaData
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_user_models_to_file():
    """Add User and SavedCart models to new_models.py if they don't exist"""
    new_models_path = Path(__file__).parent.parent / 'database' / 'new_models.py'

    # Read the file
    with open(new_models_path, 'r') as f:
        content = f.read()

    # Check if User class already exists
    if 'class User(Base):' in content:
        logger.info("✓ User and SavedCart models already exist in new_models.py")
        return

    # Add the new models
    user_models = '''

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
    items = Column(Text)  # JSON string: [{"barcode": "xxx", "quantity": 2, "name": "xxx"}, ...]
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
'''

    # Append to file
    with open(new_models_path, 'a') as f:
        f.write(user_models)

    logger.info("✅ Added User and SavedCart models to new_models.py")

def drop_all_tables():
    """Drop ALL tables from the database"""
    logger.info("=== Dropping ALL Tables ===")

    # Get metadata and reflect all existing tables
    metadata = MetaData()
    metadata.reflect(bind=engine)

    # Drop all tables in reverse order (handles foreign keys)
    metadata.drop_all(bind=engine)
    logger.info("✅ All tables dropped")

def create_new_schema_tables():
    """Create only the new schema tables"""
    logger.info("\n=== Creating New Schema Tables ===")

    # First, ensure User and SavedCart models are in the file
    add_user_models_to_file()

    # Import new models (including User and SavedCart)
    from database.new_models import Base, Chain, Branch, Product, ChainProduct, BranchPrice, User, SavedCart

    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ New schema tables created")

def initialize_chains():
    """Initialize the chains"""
    logger.info("\n=== Initializing Chains ===")

    from database.new_models import Chain

    with get_db() as db:
        # Create chains
        chains_data = [
            {'name': 'shufersal', 'display_name': 'שופרסל'},
            {'name': 'victory', 'display_name': 'ויקטורי'}
        ]

        for chain_data in chains_data:
            existing = db.query(Chain).filter(Chain.name == chain_data['name']).first()
            if not existing:
                chain = Chain(**chain_data)
                db.add(chain)
                logger.info(f"✅ Created chain: {chain_data['name']}")

        db.commit()

def import_branches_for_chain(chain_name):
    """Import branches for a specific chain"""
    logger.info(f"\nImporting branches for {chain_name}...")

    try:
        # Import the parser to get branch data
        from parsers import get_parser
        from database.new_models import Chain, Branch

        parser = get_parser(chain_name)

        # Get branch data from parser
        stores = parser.get_branch_list()

        with get_db() as db:
            # Get chain
            chain = db.query(Chain).filter(Chain.name == chain_name).first()
            if not chain:
                logger.error(f"Chain {chain_name} not found!")
                return 0

            count = 0
            for store_data in stores:
                # Check if branch exists
                existing = db.query(Branch).filter(
                    Branch.chain_id == chain.chain_id,
                    Branch.store_id == store_data['store_id']
                ).first()

                if not existing:
                    branch = Branch(
                        chain_id=chain.chain_id,
                        store_id=store_data['store_id'],
                        name=store_data.get('store_name', ''),
                        address=store_data.get('address', ''),
                        city=store_data.get('city', 'Unknown')
                    )
                    db.add(branch)
                    count += 1

            db.commit()
            logger.info(f"✅ Created {count} branches for {chain_name}")
            return count

    except Exception as e:
        logger.error(f"Error importing branches: {e}")
        return 0

def verify_setup():
    """Verify the database is set up correctly"""
    logger.info("\n=== Verifying Setup ===")

    from database.new_models import Chain, Branch, User, SavedCart

    with get_db() as db:
        # Check chains
        chains = db.query(Chain).all()
        logger.info(f"\nChains in database: {len(chains)}")
        for chain in chains:
            branch_count = db.query(Branch).filter(Branch.chain_id == chain.chain_id).count()
            logger.info(f"  - {chain.name}: {branch_count} branches")

        # Check users table
        user_count = db.query(User).count()
        logger.info(f"\nUsers table created (count: {user_count})")

        # Check saved_carts table
        cart_count = db.query(SavedCart).count()
        logger.info(f"SavedCarts table created (count: {cart_count})")

        return True

def main():
    """Main function"""
    logger.info("=== DATABASE CLEANUP AND SETUP ===\n")

    response = input("⚠️  This will DELETE ALL DATA. Continue? (yes/no): ")
    if response.lower() != 'yes':
        logger.info("Cancelled.")
        return

    try:
        # 1. Drop all tables
        drop_all_tables()

        # 2. Create new schema tables (including User and SavedCart)
        create_new_schema_tables()

        # 3. Initialize chains
        initialize_chains()

        # 4. Import branches
        branches_imported = 0
        branches_imported += import_branches_for_chain('shufersal')
        branches_imported += import_branches_for_chain('victory')

        # 5. Verify
        verify_setup()

        # 6. Summary
        logger.info("\n=== SUMMARY ===")
        logger.info("✅ Database cleaned and recreated")
        logger.info("✅ Created all tables including users and saved_carts")
        logger.info(f"✅ Created 2 chains")
        logger.info(f"✅ Imported {branches_imported} branches")

        logger.info("\n=== Next Steps ===")
        logger.info("1. Import prices:")
        logger.info("   python scripts/import_prices.py --limit 2")
        logger.info("   python scripts/import_prices.py")
        logger.info("\n2. Start developing the API endpoints for:")
        logger.info("   - User registration/login")
        logger.info("   - Cart comparison")
        logger.info("   - Saving/loading carts")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
