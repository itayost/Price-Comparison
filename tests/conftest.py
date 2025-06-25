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
from tests.fixtures.sample_products import SAMPLE_CART_ITEMS, create_test_database_data

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

@pytest.fixture(scope="session")
def setup_test_database():
    """Create database tables once per test session"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables after tests
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


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create an admin user (if your app has admin functionality)"""
    auth_service = AuthService(db_session)

    # Check if already exists
    existing = auth_service.get_user_by_email("admin@example.com")
    if existing:
        return existing

    user = auth_service.create_user(
        email="admin@example.com",
        password="adminpass123"
    )
    # Set admin flag if your User model has one
    # user.is_admin = True
    db_session.commit()
    return user


# =====================================================
# Test Data Fixtures
# =====================================================

@pytest.fixture
def test_chains(db_session: Session) -> Dict[str, Chain]:
    """Create test supermarket chains"""
    chains = {
        'shufersal': Chain(name='shufersal', display_name='שופרסל'),
        'victory': Chain(name='victory', display_name='ויקטורי')
    }

    for chain in chains.values():
        db_session.add(chain)
    db_session.commit()

    return chains


@pytest.fixture
def test_branches(db_session: Session, test_chains: Dict[str, Chain]) -> Dict[str, Branch]:
    """Create test branches in different cities"""
    branches = {
        'shufersal_dizengoff': Branch(
            chain_id=test_chains['shufersal'].chain_id,
            store_id='001',
            name='שופרסל דיזנגוף',
            address='דיזנגוף 50',
            city='תל אביב'
        ),
        'shufersal_haifa': Branch(
            chain_id=test_chains['shufersal'].chain_id,
            store_id='010',
            name='שופרסל חיפה',
            address='חורב 15',
            city='חיפה'
        ),
        'victory_tlv': Branch(
            chain_id=test_chains['victory'].chain_id,
            store_id='001',
            name='ויקטורי דיזנגוף סנטר',
            address='דיזנגוף סנטר',
            city='תל אביב'
        ),
        'victory_haifa': Branch(
            chain_id=test_chains['victory'].chain_id,
            store_id='005',
            name='ויקטורי גרנד קניון',
            address='גרנד קניון',
            city='חיפה'
        )
    }

    for branch in branches.values():
        db_session.add(branch)
    db_session.commit()

    return branches


@pytest.fixture
def test_products(db_session: Session, test_chains: Dict[str, Chain]) -> Dict[str, ChainProduct]:
    """Create test products for each chain"""
    products = {}

    # Common products available in both chains
    product_data = [
        ('7290000000001', 'חלב טרה 3%'),
        ('7290000000002', 'לחם אחיד פרוס'),
        ('7290000000003', 'ביצים L 12 יח'),
        ('7290000000004', 'עגבניות'),
        ('7290000000005', 'מים מינרלים 1.5 ליטר')
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


@pytest.fixture
def comprehensive_test_data(db_session: Session) -> Dict[str, Any]:
    """Create comprehensive test data using the helper function"""
    return create_test_database_data(db_session)


# =====================================================
# Utility Fixtures
# =====================================================

@pytest.fixture
def sample_cart_items() -> List[Dict[str, Any]]:
    """Sample cart items for comparison"""
    return SAMPLE_CART_ITEMS


@pytest.fixture
def large_cart_items() -> List[Dict[str, Any]]:
    """Large cart for performance testing"""
    return [
        {"barcode": f"729000000000{i}", "quantity": (i % 3) + 1, "name": f"מוצר {i}"}
        for i in range(1, 21)  # 20 items
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
# Service Fixtures
# =====================================================

@pytest.fixture
def auth_service(db_session: Session) -> AuthService:
    """Create AuthService instance"""
    return AuthService(db_session)


@pytest.fixture
def cart_service(db_session: Session) -> CartComparisonService:
    """Create CartComparisonService instance"""
    return CartComparisonService(db_session)


@pytest.fixture
def search_service(db_session: Session) -> ProductSearchService:
    """Create ProductSearchService instance"""
    return ProductSearchService(db_session)


# =====================================================
# Utility Fixtures
# =====================================================

@pytest.fixture
def mock_datetime(monkeypatch):
    """Mock datetime for consistent testing"""
    import datetime as dt

    class MockDatetime:
        @classmethod
        def utcnow(cls):
            return dt.datetime(2025, 1, 15, 12, 0, 0)

        @classmethod
        def now(cls):
            return dt.datetime(2025, 1, 15, 14, 0, 0)  # +2 hours for Israel time

    monkeypatch.setattr("datetime.datetime", MockDatetime)


@pytest.fixture
def hebrew_text_samples() -> Dict[str, List[str]]:
    """Sample Hebrew text for testing"""
    return {
        "product_names": ["חלב", "לחם", "ביצים", "גבינה", "עגבניות"],
        "cities": ["תל אביב", "ירושלים", "חיפה", "באר שבע"],
        "addresses": ["דיזנגוף 50", "רוטשילד 1", "הרצל 100"],
        "special_chars": ["קוטג'", "ג'ינס", "צ'יפס"]
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


# =====================================================
# Cleanup Fixtures
# =====================================================

@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Cleanup any temporary files created during tests"""
    yield
    # Cleanup code here if needed
    import tempfile
    import shutil
    temp_dir = tempfile.gettempdir()
    # Remove any test-specific temp files if created
