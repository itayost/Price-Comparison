"""
Test configuration for the price comparison server.
Focused on essential functionality.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

# Set test environment
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Import after environment is set
from database.connection import Base, get_db_session
from database.new_models import Chain, Branch, ChainProduct, BranchPrice, User
from main import app

# Simple in-memory database for tests
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Create a fresh database for each test"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = TestingSessionLocal()
    
    yield db
    
    # Cleanup
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(db):
    """Create minimal test data for price comparison"""
    # Create chains
    shufersal = Chain(
        chain_id=1, 
        name="shufersal", 
        display_name="שופרסל"
    )
    victory = Chain(
        chain_id=2, 
        name="victory", 
        display_name="ויקטורי"
    )
    db.add_all([shufersal, victory])
    
    # Create branches in Tel Aviv
    branch_shufersal = Branch(
        branch_id=1,
        chain_id=1,
        store_id="001",
        name="שופרסל דיזנגוף",
        address="דיזנגוף 50",
        city="תל אביב"
    )
    branch_victory = Branch(
        branch_id=2,
        chain_id=2,
        store_id="001", 
        name="ויקטורי סנטר",
        address="דיזנגוף סנטר",
        city="תל אביב"
    )
    db.add_all([branch_shufersal, branch_victory])
    
    # Create sample products (milk and bread)
    products = [
        ChainProduct(
            product_id=1,
            chain_id=1,
            barcode="7290000000001",
            name="חלב 3% תנובה",
            manufacturer="תנובה"
        ),
        ChainProduct(
            product_id=2,
            chain_id=2,
            barcode="7290000000001",
            name="חלב 3% תנובה",
            manufacturer="תנובה"
        ),
        ChainProduct(
            product_id=3,
            chain_id=1,
            barcode="7290000000002",
            name="לחם אחיד",
            manufacturer="אנג'ל"
        ),
        ChainProduct(
            product_id=4,
            chain_id=2,
            barcode="7290000000002",
            name="לחם אחיד",
            manufacturer="אנג'ל"
        )
    ]
    db.add_all(products)
    
    # Create prices
    prices = [
        BranchPrice(
            price_id=1,
            branch_id=1,
            product_id=1,
            barcode="7290000000001",
            price=7.90
        ),
        BranchPrice(
            price_id=2,
            branch_id=2,
            product_id=2,
            barcode="7290000000001",
            price=8.50
        ),
        BranchPrice(
            price_id=3,
            branch_id=1,
            product_id=3,
            barcode="7290000000002",
            price=5.90
        ),
        BranchPrice(
            price_id=4,
            branch_id=2,
            product_id=4,
            barcode="7290000000002",
            price=5.50
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
def auth_headers(client):
    """Create a test user and return auth headers"""
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
    
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_cart():
    """Return a sample cart for testing"""
    return {
        "city": "תל אביב",
        "items": [
            {"barcode": "7290000000001", "quantity": 2},  # Milk
            {"barcode": "7290000000002", "quantity": 1}   # Bread
        ]
    }
