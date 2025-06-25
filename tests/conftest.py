"""
Test configuration that ensures database tables are created properly.
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

# Create test database engine
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# CRITICAL: Patch database module BEFORE importing anything else
import database.connection
database.connection.engine = test_engine
database.connection.SessionLocal = TestingSessionLocal

# Force the test database URL
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# Import models and create tables BEFORE importing app
from database.new_models import Base, Chain, Branch, ChainProduct, BranchPrice, User, SavedCart

# Create all tables in the test database
Base.metadata.create_all(bind=test_engine)

# NOW import the app (it will use our patched database)
from main import app
from database.connection import get_db_session


@pytest.fixture(scope="session")
def setup_database():
    """Create tables once for all tests"""
    # Tables already created above
    yield
    # Cleanup after all tests
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db(setup_database):
    """Get a database session and clean up data after each test"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    # Override the database dependency
    app.dependency_overrides[get_db_session] = override_get_db

    # Also ensure any direct SessionLocal() calls use our test db
    # This is handled by the monkey patching above

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(db):
    """Create test data for each test"""
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
    # First, ensure we have a clean user
    existing_user = db.query(User).filter_by(email="test@example.com").first()
    if existing_user:
        db.delete(existing_user)
        db.commit()

    # Register new user
    register_response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123"
    })

    if register_response.status_code != 200:
        # If registration failed, try to understand why
        print(f"Registration failed: {register_response.text}")

    # Login
    login_response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "testpass123"
    })

    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    raise Exception(f"Failed to authenticate: {login_response.text}")


@pytest.fixture(autouse=True)
def reset_db_between_tests(db):
    """Ensure clean state between tests"""
    yield
    # Clean up any data created during the test
    db.rollback()


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
