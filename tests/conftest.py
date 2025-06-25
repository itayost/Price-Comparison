"""
Test configuration with proper database session handling.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
from datetime import datetime
import threading

# Set test environment BEFORE any imports
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["USE_ORACLE"] = "false"

# Use in-memory SQLite with proper settings for concurrency
TEST_DATABASE_URL = "sqlite:///:memory:?check_same_thread=False"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=None  # Disable pooling for SQLite
)

# Use scoped session for thread safety
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
TestingSessionLocal = scoped_session(session_factory)

# Patch database.connection BEFORE any other imports
import database.connection
database.connection.engine = test_engine
database.connection.SessionLocal = TestingSessionLocal

# Import models
from database.new_models import Base, Chain, Branch, ChainProduct, BranchPrice, User, SavedCart

# Create all tables
Base.metadata.create_all(bind=test_engine)

# Import app after database is set up
from main import app
from database.connection import get_db_session


@pytest.fixture(scope="function")
def db():
    """Create a database session for each test"""
    # Get a new session
    session = TestingSessionLocal()

    # Clean all data at start of test
    session.query(BranchPrice).delete()
    session.query(ChainProduct).delete()
    session.query(Branch).delete()
    session.query(Chain).delete()
    session.query(SavedCart).delete()
    session.query(User).delete()
    session.commit()

    yield session

    session.close()
    TestingSessionLocal.remove()  # Important for scoped_session


@pytest.fixture
def client(db):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    # Override the main database dependency
    app.dependency_overrides[get_db_session] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(db):
    """Create test data that's properly committed"""
    # Create chains
    shufersal = Chain(name="shufersal", display_name="שופרסל")
    victory = Chain(name="victory", display_name="ויקטורי")
    db.add_all([shufersal, victory])
    db.commit()  # Commit to get IDs

    # Create branches
    branch_shufersal = Branch(
        chain_id=shufersal.chain_id,
        store_id="001",
        name="שופרסל דיזנגוף",
        address="דיזנגוף 50",
        city="תל אביב"
    )
    branch_victory = Branch(
        chain_id=victory.chain_id,
        store_id="001",
        name="ויקטורי סנטר",
        address="דיזנגוף סנטר",
        city="תל אביב"
    )
    db.add_all([branch_shufersal, branch_victory])
    db.commit()

    # Create products - ensure they're properly linked
    milk_shufersal = ChainProduct(
        chain_id=shufersal.chain_id,
        barcode="7290000000001",
        name="חלב 3% תנובה"
    )
    milk_victory = ChainProduct(
        chain_id=victory.chain_id,
        barcode="7290000000001",
        name="חלב 3% תנובה"
    )
    bread_shufersal = ChainProduct(
        chain_id=shufersal.chain_id,
        barcode="7290000000002",
        name="לחם אחיד"
    )
    bread_victory = ChainProduct(
        chain_id=victory.chain_id,
        barcode="7290000000002",
        name="לחם אחיד"
    )

    products = [milk_shufersal, milk_victory, bread_shufersal, bread_victory]
    db.add_all(products)
    db.commit()

    # Create prices with proper relationships
    current_time = datetime.utcnow()
    prices = [
        BranchPrice(
            branch_id=branch_shufersal.branch_id,
            chain_product_id=milk_shufersal.chain_product_id,
            price=7.90,
            last_updated=current_time
        ),
        BranchPrice(
            branch_id=branch_victory.branch_id,
            chain_product_id=milk_victory.chain_product_id,
            price=8.50,
            last_updated=current_time
        ),
        BranchPrice(
            branch_id=branch_shufersal.branch_id,
            chain_product_id=bread_shufersal.chain_product_id,
            price=5.90,
            last_updated=current_time
        ),
        BranchPrice(
            branch_id=branch_victory.branch_id,
            chain_product_id=bread_victory.chain_product_id,
            price=5.50,
            last_updated=current_time
        )
    ]
    db.add_all(prices)
    db.commit()

    # Verify data was created
    assert db.query(Chain).count() == 2
    assert db.query(Branch).count() == 2
    assert db.query(ChainProduct).count() == 4
    assert db.query(BranchPrice).count() == 4

    # Log what was created
    print(f"Created {db.query(Chain).count()} chains")
    print(f"Created {db.query(Branch).count()} branches in תל אביב")
    print(f"Created {db.query(ChainProduct).count()} products")
    print(f"Created {db.query(BranchPrice).count()} prices")

    return {
        "chains": [shufersal, victory],
        "branches": [branch_shufersal, branch_victory],
        "products": products,
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

    if register_response.status_code != 200:
        print(f"Registration failed: {register_response.text}")

    # Login to get token
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


# Clean up at end of test session
@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Clean up after all tests"""
    def finalizer():
        TestingSessionLocal.remove()
    request.addfinalizer(finalizer)
