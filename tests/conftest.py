"""
Fixed test configuration that prevents database initialization conflicts.
Uses in-memory SQLite to avoid locking issues.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
import os
from datetime import datetime
import tempfile
from contextlib import contextmanager

# Set test environment BEFORE any imports
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["USE_ORACLE"] = "false"

# Use in-memory SQLite to avoid locking issues
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create engine with proper settings for SQLite
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=None,  # Disable pooling for in-memory database
    echo=False
)

# Use scoped session to handle thread safety
TestingSessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
)

# Patch database.connection BEFORE any other imports
import database.connection
database.connection.engine = test_engine
database.connection.SessionLocal = TestingSessionLocal

# Import models after patching
from database.new_models import Base, Chain, Branch, ChainProduct, BranchPrice, User, SavedCart

# Import app after database is set up
from main import app
from database.connection import get_db_session


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Create a session
    session = TestingSessionLocal()

    yield session

    # Cleanup
    session.close()
    TestingSessionLocal.remove()

    # Drop all tables to ensure clean state
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    # Override database dependency
    app.dependency_overrides[get_db_session] = override_get_db

    # Also patch the get_db function if it exists
    if hasattr(database.connection, 'get_db'):
        @contextmanager
        def override_get_db_context():
            try:
                yield db
            finally:
                pass
        database.connection.get_db = override_get_db_context

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(db):
    """Create comprehensive test data"""
    try:
        # Create chains
        shufersal = Chain(name="shufersal", display_name="שופרסל")
        victory = Chain(name="victory", display_name="ויקטורי")
        db.add_all([shufersal, victory])
        db.commit()

        # Refresh to get IDs
        db.refresh(shufersal)
        db.refresh(victory)

        # Create branches with exact city names
        branch_shufersal = Branch(
            chain_id=shufersal.chain_id,
            store_id="001",
            name="שופרסל דיזנגוף",
            address="דיזנגוף 50",
            city="תל אביב"  # Exact city name
        )
        branch_victory = Branch(
            chain_id=victory.chain_id,
            store_id="001",
            name="ויקטורי סנטר",
            address="דיזנגוף סנטר",
            city="תל אביב"  # Exact city name
        )
        db.add_all([branch_shufersal, branch_victory])
        db.commit()

        # Refresh to get IDs
        db.refresh(branch_shufersal)
        db.refresh(branch_victory)

        # Create products with searchable names
        products = [
            ChainProduct(
                chain_id=shufersal.chain_id,
                barcode="7290000000001",
                name="חלב 3% תנובה",
                product_id=None
            ),
            ChainProduct(
                chain_id=victory.chain_id,
                barcode="7290000000001",
                name="חלב 3% תנובה",
                product_id=None
            ),
            ChainProduct(
                chain_id=shufersal.chain_id,
                barcode="7290000000002",
                name="לחם אחיד",
                product_id=None
            ),
            ChainProduct(
                chain_id=victory.chain_id,
                barcode="7290000000002",
                name="לחם אחיד",
                product_id=None
            )
        ]
        db.add_all(products)
        db.commit()

        # Refresh products
        for product in products:
            db.refresh(product)

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
    except Exception as e:
        db.rollback()
        raise e


@pytest.fixture
def auth_headers(client, db):
    """Create a test user and return auth headers"""
    # Clear any existing test user
    existing_user = db.query(User).filter_by(email="test@example.com").first()
    if existing_user:
        db.delete(existing_user)
        db.commit()

    # Register user
    register_response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123"
    })

    if register_response.status_code != 200:
        raise Exception(f"Failed to register: {register_response.text}")

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
def auth_headers_fixed(client, db):
    """Create auth headers with proper session handling"""
    # Register a unique user for this test
    import uuid
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    register_response = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "testpass123"
    })

    if register_response.status_code != 200:
        raise Exception(f"Failed to register: {register_response.text}")

    # Login to get token
    login_response = client.post("/api/auth/login", data={
        "username": unique_email,
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


# Add session cleanup
@pytest.fixture(autouse=True)
def cleanup_sessions():
    """Ensure sessions are cleaned up after each test"""
    yield
    TestingSessionLocal.remove()
