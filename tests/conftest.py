"""
Test configuration that properly handles all database connections.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import datetime
import sys

# Set test environment BEFORE any imports
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["USE_ORACLE"] = "false"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Create test database engine
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=None  # Disable connection pooling for SQLite
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# CRITICAL: Patch database module BEFORE any other imports
import database.connection

# Replace the engine and SessionLocal
database.connection.engine = test_engine
database.connection.SessionLocal = TestingSessionLocal

# Also patch the module-level imports that might have been cached
if 'routes.product_routes' in sys.modules:
    del sys.modules['routes.product_routes']
if 'routes.cart_routes' in sys.modules:
    del sys.modules['routes.cart_routes']
if 'routes.auth_routes' in sys.modules:
    del sys.modules['routes.auth_routes']
if 'routes.saved_carts_routes' in sys.modules:
    del sys.modules['routes.saved_carts_routes']

# Import models and create tables
from database.new_models import Base, Chain, Branch, ChainProduct, BranchPrice, User, SavedCart

# Create all tables in test database
Base.metadata.create_all(bind=test_engine)

# Verify tables exist
with test_engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = [row[0] for row in result]
    print(f"Tables created in test DB: {tables}")

# NOW import the app (it will use our patched database)
from main import app
from database.connection import get_db_session


@pytest.fixture(scope="session")
def engine():
    """Provide the test engine"""
    return test_engine


@pytest.fixture(scope="function")
def db(engine):
    """Create a new database session for a test"""
    connection = engine.connect()
    transaction = connection.begin()

    # Create session bound to the connection
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """Create test client with database override"""
    # Override the main get_db_session
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db

    # Also override the route-specific get_db functions
    # Import them after module cleanup
    from routes.product_routes import get_db as product_get_db
    from routes.cart_routes import get_db as cart_get_db
    from routes.saved_carts_routes import get_db as saved_get_db

    app.dependency_overrides[product_get_db] = override_get_db
    app.dependency_overrides[cart_get_db] = override_get_db
    app.dependency_overrides[saved_get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(db):
    """Create test data"""
    # Clean any existing data
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
    """Create test user and return auth headers"""
    # Clean existing users
    db.query(User).filter_by(email="test@example.com").delete()
    db.commit()

    # Register user
    register_response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123"
    })

    if register_response.status_code != 200:
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
