"""
Test configuration with proper initialization order.
"""
import pytest
import os
from datetime import datetime

# 1. Set environment FIRST
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["USE_ORACLE"] = "false"

# 2. Set up test database
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(bind=test_engine)

# 3. Monkey-patch database connection BEFORE any imports
import database.connection
database.connection.engine = test_engine
database.connection.SessionLocal = TestSessionLocal
database.connection.get_db_session = lambda: TestSessionLocal()

# 4. Import models and create tables
from database.new_models import Base, User, Chain, Branch, ChainProduct, BranchPrice, SavedCart
Base.metadata.drop_all(bind=test_engine)
Base.metadata.create_all(bind=test_engine)

# 5. Import FastAPI app
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def db():
    """Database session for tests"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    # Clear all data
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """Test client with db override"""
    def get_test_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[database.connection.get_db_session] = get_test_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(db):
    """Create sample data"""
    # Create chains
    shufersal = Chain(name="shufersal", display_name="שופרסל")
    victory = Chain(name="victory", display_name="ויקטורי")
    db.add_all([shufersal, victory])
    db.commit()

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

    # Create products
    products = []
    for chain_id, chain_name in [(shufersal.chain_id, "shufersal"), (victory.chain_id, "victory")]:
        for barcode, name in [("7290000000001", "חלב 3% תנובה"), ("7290000000002", "לחם אחיד")]:
            product = ChainProduct(
                chain_id=chain_id,
                barcode=barcode,
                name=name
            )
            products.append(product)
    db.add_all(products)
    db.commit()

    # Create prices
    prices = [
        BranchPrice(
            branch_id=branch_shufersal.branch_id,
            chain_product_id=products[0].chain_product_id,
            price=7.90,
            last_updated=datetime.utcnow()
        ),
        BranchPrice(
            branch_id=branch_victory.branch_id,
            chain_product_id=products[1].chain_product_id,
            price=8.50,
            last_updated=datetime.utcnow()
        ),
        BranchPrice(
            branch_id=branch_shufersal.branch_id,
            chain_product_id=products[2].chain_product_id,
            price=5.90,
            last_updated=datetime.utcnow()
        ),
        BranchPrice(
            branch_id=branch_victory.branch_id,
            chain_product_id=products[3].chain_product_id,
            price=5.50,
            last_updated=datetime.utcnow()
        )
    ]
    db.add_all(prices)
    db.commit()

    return {"success": True}


@pytest.fixture
def auth_headers(client, db):
    """Get auth headers"""
    # Register user
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123"
    })

    # Login
    response = client.post("/api/auth/login", data={
        "username": "test@example.com",
        "password": "testpass123"
    })

    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return {}


@pytest.fixture
def auth_headers_fixed(client, db):
    """Get unique auth headers"""
    import uuid
    email = f"test_{uuid.uuid4().hex[:6]}@example.com"

    # Register
    reg_response = client.post("/api/auth/register", json={
        "email": email,
        "password": "testpass123"
    })

    if reg_response.status_code != 200:
        pytest.skip(f"Could not register user: {reg_response.text}")

    # Login
    login_response = client.post("/api/auth/login", data={
        "username": email,
        "password": "testpass123"
    })

    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    pytest.skip(f"Could not login: {login_response.text}")


# Clean up after tests
def pytest_sessionfinish(session, exitstatus):
    """Clean up test database"""
    import os
    if os.path.exists("test.db"):
        try:
            os.remove("test.db")
        except:
            pass
