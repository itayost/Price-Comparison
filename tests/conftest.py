"""
Pytest configuration and shared fixtures for all tests.

This module provides:
- Test database setup with SQLite in-memory
- FastAPI test client configuration
- Authentication fixtures
- Test data fixtures (chains, branches, products, prices)
- Utility fixtures and markers
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import sys
import os
from datetime import datetime
from typing import Generator, Dict, Any, List
import json

# Set testing environment variables
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-12345"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Add the parent directory to the path so we can import from the main app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path is set
from database.connection import Base, get_db_session
from database.new_models import (
    Chain, Branch, Product, ChainProduct, BranchPrice,
    User, SavedCart
)
from services.auth_service import AuthService
from services.cart_service import CartComparisonService, CartItem
from services.product_search_service import ProductSearchService
from main import app

# =====================================================
# Database Setup
# =====================================================

# Test database configuration - using in-memory SQLite
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine with proper settings for SQLite
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite
    poolclass=StaticPool,  # Use StaticPool for in-memory database
)

# Create session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =====================================================
# Core Fixtures
# =====================================================

@pytest.fixture(scope="function")
def setup_test_database():
    """Create database tables for each test function"""
    # Import all models to ensure they're registered with Base
    from database.new_models import (
        Chain, Branch, Product, ChainProduct, BranchPrice,
        User, SavedCart
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(setup_test_database) -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.
    Uses transaction rollback to ensure test isolation.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Configure session for testing
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.expire_all()
            session.begin_nested()

    yield session

    # Cleanup
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Create a FastAPI test client with database override.
    This client will use the test database session for all requests.
    """
    # Override the database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture

    app.dependency_overrides[get_db_session] = override_get_db

    # Create test client
    with TestClient(app) as test_client:
        yield test_client

    # Clear dependency overrides
    app.dependency_overrides.clear()


# =====================================================
# Authentication Fixtures
# =====================================================

@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user for authentication tests"""
    auth_service = AuthService(db_session)

    # Check if user already exists
    existing_user = auth_service.get_user_by_email("testuser@example.com")
    if existing_user:
        return existing_user

    # Create new user
    user = auth_service.create_user(
        email="testuser@example.com",
        password="testpass123"
    )
    db_session.commit()
    return user


@pytest.fixture
def auth_headers(client: TestClient, test_user: User) -> Dict[str, str]:
    """Get authentication headers with valid JWT token"""
    response = client.post(
        "/api/auth/login",
        data={
            "username": test_user.email,
            "password": "testpass123"
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =====================================================
# Test Data Fixtures
# =====================================================

@pytest.fixture
def test_chains(db_session: Session) -> Dict[str, Chain]:
    """Create test chains with proper cleanup"""
    # Clear existing chains first
    db_session.query(Chain).delete()
    db_session.commit()

    chains = {}
    chain_data = [
        ('shufersal', 'שופרסל'),
        ('victory', 'ויקטורי'),
        ('yochananof', 'יוחננוף')
    ]

    for name, display_name in chain_data:
        chain = Chain(name=name, display_name=display_name)
        db_session.add(chain)
        chains[name] = chain

    db_session.commit()
    return chains


@pytest.fixture
def test_branches(db_session: Session, test_chains: Dict[str, Chain]) -> Dict[str, Branch]:
    """Create test branches in different cities"""
    branches = {}

    # Shufersal branches
    branches['shufersal_dizengoff'] = Branch(
        chain_id=test_chains['shufersal'].chain_id,
        branch_id="001",
        name="שופרסל דיזנגוף",
        city="תל אביב",
        address="דיזנגוף 50"
    )

    branches['shufersal_haifa'] = Branch(
        chain_id=test_chains['shufersal'].chain_id,
        branch_id="002",
        name="שופרסל חיפה",
        city="חיפה",
        address="הרצל 15"
    )

    # Victory branches
    branches['victory_tlv'] = Branch(
        chain_id=test_chains['victory'].chain_id,
        branch_id="101",
        name="ויקטורי תל אביב",
        city="תל אביב",
        address="אלנבי 100"
    )

    branches['victory_haifa'] = Branch(
        chain_id=test_chains['victory'].chain_id,
        branch_id="102",
        name="ויקטורי חיפה",
        city="חיפה",
        address="בן גוריון 50"
    )

    for branch in branches.values():
        db_session.add(branch)

    db_session.commit()
    return branches


@pytest.fixture
def test_products(db_session: Session, test_chains: Dict[str, Chain]) -> Dict[str, ChainProduct]:
    """Create test products for chains"""
    products = {}

    # Product data: (barcode, name)
    product_data = [
        ('7290000000001', 'חלב טרה 3%'),
        ('7290000000002', 'לחם אחיד'),
        ('7290000000003', 'ביצים L')
    ]

    for chain_name, chain in test_chains.items():
        for barcode, name in product_data:
            key = f"{chain_name}_{barcode}"
            products[key] = ChainProduct(
                chain_id=chain.chain_id,
                barcode=barcode,
                name=name if chain_name == 'shufersal' else name.replace('טרה', 'תנובה')
            )
            db_session.add(products[key])

    db_session.commit()
    return products


@pytest.fixture
def test_prices(
    db_session: Session,
    test_branches: Dict[str, Branch],
    test_products: Dict[str, ChainProduct]
) -> Dict[str, BranchPrice]:
    """Create test prices for products in branches"""
    prices = {}

    # Price mapping
    price_data = [
        ('shufersal_dizengoff', 'shufersal_7290000000001', 5.90),
        ('shufersal_dizengoff', 'shufersal_7290000000002', 7.50),
        ('shufersal_dizengoff', 'shufersal_7290000000003', 14.90),
        ('victory_tlv', 'victory_7290000000001', 5.50),
        ('victory_tlv', 'victory_7290000000002', 8.90),
        ('victory_tlv', 'victory_7290000000003', 13.90),
        ('shufersal_haifa', 'shufersal_7290000000001', 5.50),
        ('shufersal_haifa', 'shufersal_7290000000002', 6.90),
        ('victory_haifa', 'victory_7290000000001', 5.20),
        ('victory_haifa', 'victory_7290000000002', 7.90)
    ]

    for branch_key, product_key, price_value in price_data:
        if branch_key in test_branches and product_key in test_products:
            key = f"{branch_key}_{product_key}"
            prices[key] = BranchPrice(
                chain_product_id=test_products[product_key].chain_product_id,
                branch_id=test_branches[branch_key].branch_id,
                price=price_value,
                last_updated=datetime.utcnow()
            )
            db_session.add(prices[key])

    db_session.commit()
    return prices


# =====================================================
# Utility Fixtures
# =====================================================

@pytest.fixture
def sample_cart_items() -> List[Dict[str, Any]]:
    """Sample cart items for comparison"""
    return [
        {"barcode": "7290000000001", "quantity": 2, "name": "חלב טרה 3%"},
        {"barcode": "7290000000002", "quantity": 1, "name": "לחם אחיד"},
        {"barcode": "7290000000003", "quantity": 3, "name": "ביצים L"}
    ]


@pytest.fixture
def saved_cart_data(test_user: User, sample_cart_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Sample saved cart data"""
    return {
        "user_id": test_user.user_id,
        "cart_name": "הקניות השבועיות",
        "city": "תל אביב",
        "items": json.dumps(sample_cart_items, ensure_ascii=False)
    }


# =====================================================
# Test Markers
# =====================================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests that run in isolation")
    config.addinivalue_line("markers", "integration: Integration tests requiring database")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")
    config.addinivalue_line("markers", "auth: Authentication-related tests")
    config.addinivalue_line("markers", "cart: Cart functionality tests")
    config.addinivalue_line("markers", "hebrew: Tests involving Hebrew text")


# =====================================================
# Pytest Hooks
# =====================================================

def pytest_collection_modifyitems(config, items):
    """Automatically add markers based on test location"""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "api" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add markers based on test name
        if "auth" in item.name:
            item.add_marker(pytest.mark.auth)
        if "cart" in item.name:
            item.add_marker(pytest.mark.cart)
        if "hebrew" in item.name or "hebrew" in str(item.fspath):
            item.add_marker(pytest.mark.hebrew)
