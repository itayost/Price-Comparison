# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database.connection import Base, get_db
from database.new_models import Chain, Branch, ChainProduct, BranchPrice

# Create a test database (using SQLite for simplicity in tests)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override the database dependency to use test database"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the dependency in our app
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def setup_database():
    """Create all tables before tests, drop them after"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(setup_database):
    """Create a test client for making API requests"""
    return TestClient(app)

@pytest.fixture
def sample_data(setup_database):
    """Add some sample data for tests"""
    db = TestingSessionLocal()
    
    # Add chains
    shufersal = Chain(name='shufersal', display_name='שופרסל')
    victory = Chain(name='victory', display_name='ויקטורי')
    db.add(shufersal)
    db.add(victory)
    db.commit()
    
    # Add branches
    branch1 = Branch(
        chain_id=shufersal.chain_id,
        store_id='001',
        name='שופרסל דיזנגוף',
        address='דיזנגוף 50',
        city='תל אביב'
    )
    branch2 = Branch(
        chain_id=victory.chain_id,
        store_id='001',
        name='ויקטורי רמת אביב',
        address='איינשטיין 40',
        city='תל אביב'
    )
    db.add(branch1)
    db.add(branch2)
    db.commit()
    
    # Add products and prices
    milk = ChainProduct(
        chain_id=shufersal.chain_id,
        barcode='7290000000001',
        name='חלב 3% טרה 1 ליטר'
    )
    db.add(milk)
    db.commit()
    
    # Add price
    price = BranchPrice(
        chain_product_id=milk.chain_product_id,
        branch_id=branch1.branch_id,
        price=5.90
    )
    db.add(price)
    db.commit()
    
    yield  # This is where the test runs
    
    # Cleanup after test
    db.query(BranchPrice).delete()
    db.query(ChainProduct).delete()
    db.query(Branch).delete()
    db.query(Chain).delete()
    db.commit()
    db.close()
