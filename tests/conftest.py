"""
Simplified test configuration that works with the actual database setup.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
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

# Patch database.connection BEFORE any other imports
import database.connection
database.connection.engine = test_engine
database.connection.SessionLocal = TestingSessionLocal

# Import models and create tables
from database.new_models import Base, Chain, Branch, ChainProduct, BranchPrice, User, SavedCart

# Create all tables
Base.metadata.create_all(bind=test_engine)
print(f"Tables created: {Base.metadata.tables.keys()}")

# Import app after database is set up
from main import app
from database.connection import get_db_session


@pytest.fixture(scope="function")
def db():
    """Create a database session for each test"""
    # Each test gets its own connection/transaction
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

    # Override the main database dependency used by all routes
    app.dependency_overrides[get_db_session] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(db):
    """Create test data for each test"""
    # Clean existing data
    db.query(BranchPrice).delete()
    db.query(ChainProduct).delete()
    db.query(Branch).delete()
    db.query(Chain).delete()
    db.commit()

    # Create chains
    shufersal = Chain(name="shufersal", display_name="שופרסל")
    victory = Chain(name="victory", display_name="ויקטורי")
    db.add_all([shufersal, victory])
    db.flush()

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
    db.flush()

    # Create products
    products = [
        ChainProduct(
            chain_id=shufersal.chain_id,
            barcode="7290000000001",
            name="חלב 3% תנובה"
        ),
        ChainProduct(
            chain_id=victory.chain_id,
            barcode="7290000000001",
            name="חלב 3% תנובה"
        ),
        ChainProduct(
            chain_id=shufersal.chain_id,
            barcode="7290000000002",
            name="לחם אחיד"
        ),
        ChainProduct(
            chain_id=victory.chain_id,
            barcode="7290000000002",
            name="לחם אחיד"
        )
    ]
    db.add_all(products)
    db.flush()

    # Create prices
    current_time = datetime.utcnow()
    prices = [
        BranchPrice(
            branch_id=branch_shufersal.branch_id,
            chain_product_id=products[0].chain_product_id,
            price=7.90,
            last_updated=current_time
        ),
        BranchPrice(
            branch_id=branch_victory.branch_id,
            chain_product_id=products[1].chain_product_id,
            price=8.50,
            last_updated=current_time
        ),
        BranchPrice(
            branch_id=branch_shufersal.branch_id,
            chain_product_id=products[2].chain_product_id,
            price=5.90,
            last_updated=current_time
        ),
        BranchPrice(
            branch_id=branch_victory.branch_id,
            chain_product_id=products[3].chain_product_id,
            price=5.50,
            last_updated=current_time
        )
    ]
    db.add_all(prices)
    db.commit()

    return {
        "chains": [shufersal, victory],
        "branches": [branch_shufersal, branch_victory],
        "products": products,
        "prices": prices
    }


@pytest.fixture
def auth_headers(client, db):
    """Create a test user and return auth headers"""
    # Clean any existing test user
    db.query(User).filter_by(email="test@example.com").delete()
    db.commit()

    # Register user
    register_response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123"
    })

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
