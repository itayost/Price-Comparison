# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import sys
import os

# Set testing environment
os.environ["TESTING"] = "true"

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path is set
from database.connection import Base
from database.new_models import Chain, Branch, ChainProduct, BranchPrice, User, SavedCart

# Create a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override function
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    """Create a test client"""
    # Import here to avoid circular imports
    from main import app
    from database.connection import get_db_session

    # Override dependency
    app.dependency_overrides[get_db_session] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def db_session():
    """Create a database session for tests"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def sample_data(db_session):
    """Add comprehensive sample data for tests"""
    # Clear existing data
    db_session.query(BranchPrice).delete()
    db_session.query(ChainProduct).delete()
    db_session.query(Branch).delete()
    db_session.query(Chain).delete()
    db_session.query(SavedCart).delete()
    db_session.query(User).delete()
    db_session.commit()

    # Add chains
    shufersal = Chain(name='shufersal', display_name='שופרסל')
    victory = Chain(name='victory', display_name='ויקטורי')
    db_session.add_all([shufersal, victory])
    db_session.commit()

    # Add branches
    branch1 = Branch(
        chain_id=shufersal.chain_id,
        store_id='001',
        name='שופרסל דיזנגוף',
        address='דיזנגוף 50',
        city='תל אביב'
    )
    branch2 = Branch(
        chain_id=victory.chain_id,
        store_id='001',
        name='ויקטורי רמת אביב',
        address='איינשטיין 40',
        city='תל אביב'
    )
    db_session.add_all([branch1, branch2])
    db_session.commit()

    # Add products for both chains
    products = [
        # Shufersal products
        ChainProduct(
            chain_id=shufersal.chain_id,
            barcode='7290000000001',
            name='חלב 3% טרה 1 ליטר'
        ),
        ChainProduct(
            chain_id=shufersal.chain_id,
            barcode='7290000000002',
            name='לחם אחיד'
        ),
        ChainProduct(
            chain_id=shufersal.chain_id,
            barcode='7290000000003',
            name='ביצים L 12 יח'
        ),
        # Victory products
        ChainProduct(
            chain_id=victory.chain_id,
            barcode='7290000000001',
            name='חלב טרה 3% 1 ליטר'
        ),
        ChainProduct(
            chain_id=victory.chain_id,
            barcode='7290000000002',
            name='לחם אחיד פרוס'
        ),
    ]
    db_session.add_all(products)
    db_session.commit()

    # Add prices
    prices = [
        # Shufersal prices
        BranchPrice(
            chain_product_id=products[0].chain_product_id,
            branch_id=branch1.branch_id,
            price=5.90
        ),
        BranchPrice(
            chain_product_id=products[1].chain_product_id,
            branch_id=branch1.branch_id,
            price=7.50
        ),
        BranchPrice(
            chain_product_id=products[2].chain_product_id,
            branch_id=branch1.branch_id,
            price=12.90
        ),
        # Victory prices
        BranchPrice(
            chain_product_id=products[3].chain_product_id,
            branch_id=branch2.branch_id,
            price=6.20
        ),
        BranchPrice(
            chain_product_id=products[4].chain_product_id,
            branch_id=branch2.branch_id,
            price=6.90
        ),
    ]
    db_session.add_all(prices)
    db_session.commit()

    yield db_session

    # Cleanup
    db_session.query(BranchPrice).delete()
    db_session.query(ChainProduct).delete()
    db_session.query(Branch).delete()
    db_session.query(Chain).delete()
    db_session.query(SavedCart).delete()
    db_session.query(User).delete()
    db_session.commit()
