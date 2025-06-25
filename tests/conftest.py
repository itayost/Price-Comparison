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
from services.cart_service import CartComparisonService
from services.product_search_service import ProductSearchService
from main import app
from tests.fixtures.sample_products import SAMPLE_CART_ITEMS

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
        'victory': Chain(name='victory', display_name='ויקטורי'),
        'rami_levy': Chain(name='rami_levy', display_name='רמי לוי')
    }

    db_session.add_all(chains.values())
    db_session.commit()

    return chains


@pytest.fixture
def test_branches(db_session: Session, test_chains: Dict[str, Chain]) -> Dict[str, Branch]:
    """Create test branches in multiple cities"""
    branches = {
        # Tel Aviv branches
        'shufersal_dizengoff': Branch(
            chain_id=test_chains['shufersal'].chain_id,
            store_id='001',
            name='שופרסל דיזנגוף',
            address='דיזנגוף 50',
            city='תל אביב'
        ),
        'shufersal_ramat_aviv': Branch(
            chain_id=test_chains['shufersal'].chain_id,
            store_id='002',
            name='שופרסל רמת אביב',
            address='איינשטיין 40',
            city='תל אביב'
        ),
        'victory_center': Branch(
            chain_id=test_chains['victory'].chain_id,
            store_id='001',
            name='ויקטורי סנטר',
            address='דיזנגוף סנטר',
            city='תל אביב'
        ),
        'victory_port': Branch(
            chain_id=test_chains['victory'].chain_id,
            store_id='002',
            name='ויקטורי נמל תל אביב',
            address='הנמל 24',
            city='תל אביב'
        ),

        # Haifa branches
        'shufersal_haifa': Branch(
            chain_id=test_chains['shufersal'].chain_id,
            store_id='010',
            name='שופרסל חיפה',
            address='שדרות הנשיא 100',
            city='חיפה'
        ),
        'rami_levy_haifa': Branch(
            chain_id=test_chains['rami_levy'].chain_id,
            store_id='001',
            name='רמי לוי חיפה',
            address='דרך יפו 50',
            city='חיפה'
        )
    }

    db_session.add_all(branches.values())
    db_session.commit()

    return branches


@pytest.fixture
def test_products(db_session: Session, test_chains: Dict[str, Chain]) -> Dict[str, ChainProduct]:
    """Create test products for all chains"""
    products = {}

    # Common products with variations in naming between chains
    product_data = [
        ('7290000000001', 'חלב טרה 3% 1 ליטר', 'חלב 3% טרה 1 ליטר', 'חלב טרה 3%'),
        ('7290000000002', 'לחם אחיד פרוס', 'לחם אחיד', 'לחם לבן פרוס'),
        ('7290000000003', 'ביצים L 12 יחידות', 'ביצים גודל L', 'ביצים L תריסר'),
        ('7290000000004', 'קוטג׳ 5%', 'גבינת קוטג׳ 5%', 'קוטג 5% טרה'),
        ('7290000000005', 'עגבניות', 'עגבניות שרי', 'עגבניות אשכול'),
        ('7290000000006', 'חומוס אחלה', 'חומוס אחלה 400 גרם', 'חומוס אחלה'),
        ('7290000000007', 'קולה 1.5 ליטר', 'קוקה קולה 1.5L', 'קוקה קולה 1.5'),
        ('7290000000008', 'אורז פרסי', 'אורז פרסי 1 קג', 'אורז לבן פרסי'),
        ('7290000000009', 'שמן זית', 'שמן זית כתית', 'שמן זית בכתית'),
        ('7290000000010', 'סוכר לבן', 'סוכר לבן 1 קג', 'סוכר גבישי')
    ]

    # Create products for each chain
    for i, (barcode, shufersal_name, victory_name, rami_levy_name) in enumerate(product_data):
        # Shufersal product
        if 'shufersal' in test_chains:
            shufersal_product = ChainProduct(
                chain_id=test_chains['shufersal'].chain_id,
                barcode=barcode,
                name=shufersal_name
            )
            products[f'shufersal_{barcode}'] = shufersal_product

        # Victory product
        if 'victory' in test_chains:
            victory_product = ChainProduct(
                chain_id=test_chains['victory'].chain_id,
                barcode=barcode,
                name=victory_name
            )
            products[f'victory_{barcode}'] = victory_product

        # Rami Levy product
        if 'rami_levy' in test_chains:
            rami_levy_product = ChainProduct(
                chain_id=test_chains['rami_levy'].chain_id,
                barcode=barcode,
                name=rami_levy_name
            )
            products[f'rami_levy_{barcode}'] = rami_levy_product

    db_session.add_all(products.values())
    db_session.commit()

    return products


@pytest.fixture
def test_prices(db_session: Session, test_branches: Dict[str, Branch],
                test_products: Dict[str, ChainProduct]) -> Dict[str, BranchPrice]:
    """Create realistic test prices for products at different branches"""
    prices = {}

    # Realistic price data (barcode -> chain -> price)
    price_data = {
        '7290000000001': {'shufersal': 5.90, 'victory': 6.20, 'rami_levy': 5.50},   # Milk
        '7290000000002': {'shufersal': 7.50, 'victory': 6.90, 'rami_levy': 6.50},   # Bread
        '7290000000003': {'shufersal': 12.90, 'victory': 13.50, 'rami_levy': 11.90}, # Eggs
        '7290000000004': {'shufersal': 4.50, 'victory': 4.50, 'rami_levy': 4.20},   # Cottage
        '7290000000005': {'shufersal': 8.90, 'victory': 7.90, 'rami_levy': 8.50},   # Tomatoes
        '7290000000006': {'shufersal': 9.90, 'victory': 10.50, 'rami_levy': 8.90},  # Hummus
        '7290000000007': {'shufersal': 7.90, 'victory': 8.50, 'rami_levy': 7.50},   # Cola
        '7290000000008': {'shufersal': 12.90, 'victory': 13.90, 'rami_levy': 11.50}, # Rice
        '7290000000009': {'shufersal': 29.90, 'victory': 31.90, 'rami_levy': 27.90}, # Olive Oil
        '7290000000010': {'shufersal': 5.90, 'victory': 5.50, 'rami_levy': 5.20}    # Sugar
    }

    # Create prices for each product at each branch
    for barcode, chain_prices in price_data.items():
        for chain_name, price in chain_prices.items():
            product_key = f'{chain_name}_{barcode}'
            if product_key in test_products:
                product = test_products[product_key]

                # Add price to all branches of this chain
                for branch_key, branch in test_branches.items():
                    if chain_name in branch_key:
                        branch_price = BranchPrice(
                            chain_product_id=product.chain_product_id,
                            branch_id=branch.branch_id,
                            price=price,
                            last_updated=datetime.utcnow()
                        )
                        prices[f'{branch_key}_{barcode}'] = branch_price

    db_session.add_all(prices.values())
    db_session.commit()

    return prices


# =====================================================
# Sample Data Fixtures
# =====================================================

@pytest.fixture
def sample_cart_items() -> List[Dict[str, Any]]:
    """Sample cart items for testing cart comparison"""
    return [
        {"barcode": "7290000000001", "quantity": 2, "name": "חלב"},
        {"barcode": "7290000000002", "quantity": 1, "name": "לחם"},
        {"barcode": "7290000000003", "quantity": 1, "name": "ביצים"}
    ]


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
def hebrew_text_samples() -> Dict[str, str]:
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
