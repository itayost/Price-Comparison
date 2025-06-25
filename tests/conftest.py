# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import sys
import os
from datetime import datetime
from typing import Generator, Dict, Any
import json

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-12345"

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path is set
from database.connection import Base
from database.new_models import Chain, Branch, ChainProduct, BranchPrice, User, SavedCart
from services.auth_service import AuthService

# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine with proper settings for SQLite
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Use StaticPool for in-memory database
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Database session override
def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def setup_test_env():
    """Setup test environment once per session"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(setup_test_env) -> Generator[Session, None, None]:
    """Create a fresh database session for each test"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override"""
    from main import app
    from database.connection import get_db_session

    # Override database dependency
    app.dependency_overrides[get_db_session] = lambda: db_session

    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient, test_user: User) -> Dict[str, str]:
    """Get authentication headers for a test user"""
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
def test_user(db_session: Session) -> User:
    """Create a test user"""
    auth_service = AuthService(db_session)
    user = auth_service.create_user(
        email="testuser@example.com",
        password="testpass123"
    )
    db_session.commit()
    return user


@pytest.fixture
def test_chains(db_session: Session) -> Dict[str, Chain]:
    """Create test chains"""
    shufersal = Chain(name='shufersal', display_name='שופרסל')
    victory = Chain(name='victory', display_name='ויקטורי')

    db_session.add_all([shufersal, victory])
    db_session.commit()

    return {
        'shufersal': shufersal,
        'victory': victory
    }


@pytest.fixture
def test_branches(db_session: Session, test_chains: Dict[str, Chain]) -> Dict[str, Branch]:
    """Create test branches in Tel Aviv"""
    branches = {
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
        )
    }

    db_session.add_all(branches.values())
    db_session.commit()

    return branches


@pytest.fixture
def test_products(db_session: Session, test_chains: Dict[str, Chain]) -> Dict[str, ChainProduct]:
    """Create test products for both chains"""
    products = {}

    # Common products (same barcode, different chains)
    common_items = [
        ('7290000000001', 'חלב טרה 3% 1 ליטר', 'חלב 3% טרה 1 ליטר'),
        ('7290000000002', 'לחם אחיד פרוס', 'לחם אחיד'),
        ('7290000000003', 'ביצים L 12 יחידות', 'ביצים גודל L'),
        ('7290000000004', 'קוטג׳ 5%', 'גבינת קוטג׳ 5%'),
        ('7290000000005', 'עגבניות', 'עגבניות שרי')
    ]

    # Create products for each chain
    for barcode, shufersal_name, victory_name in common_items:
        # Shufersal product
        shufersal_product = ChainProduct(
            chain_id=test_chains['shufersal'].chain_id,
            barcode=barcode,
            name=shufersal_name
        )
        products[f'shufersal_{barcode}'] = shufersal_product

        # Victory product (might have slightly different name)
        victory_product = ChainProduct(
            chain_id=test_chains['victory'].chain_id,
            barcode=barcode,
            name=victory_name
        )
        products[f'victory_{barcode}'] = victory_product

    db_session.add_all(products.values())
    db_session.commit()

    return products


@pytest.fixture
def test_prices(db_session: Session, test_branches: Dict[str, Branch],
                test_products: Dict[str, ChainProduct]) -> Dict[str, BranchPrice]:
    """Create test prices for products at different branches"""
    prices = {}

    # Price variations for testing cheapest store logic
    price_data = {
        '7290000000001': {'shufersal': 5.90, 'victory': 6.20},  # Milk - Shufersal cheaper
        '7290000000002': {'shufersal': 7.50, 'victory': 6.90},  # Bread - Victory cheaper
        '7290000000003': {'shufersal': 12.90, 'victory': 13.50}, # Eggs - Shufersal cheaper
        '7290000000004': {'shufersal': 4.50, 'victory': 4.50},  # Cottage - Same price
        '7290000000005': {'shufersal': 8.90, 'victory': 7.90},  # Tomatoes - Victory cheaper
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


@pytest.fixture
def sample_cart_items() -> list:
    """Sample cart items for testing"""
    return [
        {"barcode": "7290000000001", "quantity": 2, "name": "חלב"},
        {"barcode": "7290000000002", "quantity": 1, "name": "לחם"},
        {"barcode": "7290000000003", "quantity": 1, "name": "ביצים"}
    ]


@pytest.fixture
def mock_datetime(freezegun):
    """Mock datetime for consistent testing"""
    # This fixture is available when using freezegun
    pass


# Markers for test categorization
pytest.mark.unit = pytest.mark.mark(name="unit")
pytest.mark.integration = pytest.mark.mark(name="integration")
pytest.mark.slow = pytest.mark.mark(name="slow")
