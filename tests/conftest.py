"""
Simplified test configuration that properly handles database setup.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime

# Set test environment BEFORE any imports
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["USE_ORACLE"] = "false"

# Create test database
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Monkey patch the database module BEFORE importing anything else
import database.connection
database.connection.SessionLocal = TestingSessionLocal
database.connection.engine = engine

# Force override the database URL
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# NOW we can safely import everything else
from database.new_models import Base, Chain, Branch, ChainProduct, BranchPrice, User, SavedCart
from main import app


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    """Create test client with database override"""
    # Override all possible database dependencies
    def override_get_db():
        try:
            yield db
        finally:
            pass

    # Import all the get_db functions from different modules
    from database.connection import get_db_session

    # Override the main one
    app.dependency_overrides[get_db_session] = override_get_db

    # The routes use their own get_db functions that create new sessions
    # We need to patch SessionLocal at the module level (already done above)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(db):
    """Create test data"""
    # Create chains
    shufersal = Chain(name="shufersal", display_name="שופרסל")
    victory = Chain(name="victory", display_name="ויקטורי")
    db.add_all([shufersal, victory])
    db.flush()

    # Create branches
    branch_s = Branch(
        chain_id=shufersal.chain_id,
        store_id="001",
        name="שופרסל דיזנגוף",
        address="דיזנגוף 50",
        city="תל אביב"
    )
    branch_v = Branch(
        chain_id=victory.chain_id,
        store_id="001",
        name="ויקטורי סנטר",
        address="דיזנגוף סנטר",
        city="תל אביב"
    )
    db.add_all([branch_s, branch_v])
    db.flush()

    # Create products
    milk_s = ChainProduct(
        chain_id=shufersal.chain_id,
        barcode="7290000000001",
        name="חלב 3% תנובה"
    )
    milk_v = ChainProduct(
        chain_id=victory.chain_id,
        barcode="7290000000001",
        name="חלב 3% תנובה"
    )
    bread_s = ChainProduct(
        chain_id=shufersal.chain_id,
        barcode="7290000000002",
        name="לחם אחיד"
    )
    bread_v = ChainProduct(
        chain_id=victory.chain_id,
        barcode="7290000000002",
        name="לחם אחיד"
    )
    db.add_all([milk_s, milk_v, bread_s, bread_v])
    db.flush()

    # Create prices
    prices = [
        BranchPrice(
            branch_id=branch_s.branch_id,
            chain_product_id=milk_s.chain_product_id,
            price=7.90,
            last_updated=datetime.utcnow()
        ),
        BranchPrice(
            branch_id=branch_v.branch_id,
            chain_product_id=milk_v.chain_product_id,
            price=8.50,
            last_updated=datetime.utcnow()
        ),
        BranchPrice(
            branch_id=branch_s.branch_id,
            chain_product_id=bread_s.chain_product_id,
            price=5.90,
            last_updated=datetime.utcnow()
        ),
        BranchPrice(
            branch_id=branch_v.branch_id,
            chain_product_id=bread_v.chain_product_id,
            price=5.50,
            last_updated=datetime.utcnow()
        )
    ]
    db.add_all(prices)
    db.commit()

    return {
        "chains": [shufersal, victory],
        "branches": [branch_s, branch_v],
        "products": [milk_s, milk_v, bread_s, bread_v],
        "prices": prices
    }


@pytest.fixture
def auth_headers(client, db):
    """Create a test user and return auth headers"""
    # Register user
    register_response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123"
    })

    # Login
    login_response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "testpass123"
    })

    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    # Try without registering (user might exist)
    login_response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "testpass123"
    })

    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    raise Exception(f"Failed to authenticate: {login_response.text}")


@pytest.fixture
def sample_cart():
    """Sample cart for testing"""
    return {
        "city": "תל אביב",
        "items": [
            {"barcode": "7290000000001", "quantity": 2},
            {"barcode": "7290000000002", "quantity": 1}
        ]
    }
