#!/usr/bin/env python3
"""
Diagnostic script to identify real issues with the server
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.new_models import Chain, Branch, ChainProduct, BranchPrice, Base
from services.product_search_service import ProductSearchService

# Create test database connection
engine = create_engine("sqlite:///./test_diagnostic.db", echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def diagnose_database():
    """Check database setup and data"""
    print("\n" + "="*50)
    print("DATABASE DIAGNOSTIC")
    print("="*50)
    
    session = Session()
    
    # Check if tables exist
    try:
        # Check table existence
        tables = engine.table_names()
        print(f"\nTables found: {tables}")
        
        # Check data
        chains = session.query(Chain).all()
        print(f"\nChains: {len(chains)}")
        for chain in chains:
            print(f"  - {chain.name} (ID: {chain.chain_id})")
        
        branches = session.query(Branch).all()
        print(f"\nBranches: {len(branches)}")
        for branch in branches:
            print(f"  - {branch.name} in '{branch.city}' (Chain ID: {branch.chain_id})")
        
        products = session.query(ChainProduct).all()
        print(f"\nProducts: {len(products)}")
        for product in products[:5]:  # First 5
            print(f"  - {product.name} ({product.barcode})")
        
        prices = session.query(BranchPrice).count()
        print(f"\nTotal prices: {prices}")
        
    except Exception as e:
        print(f"\nERROR checking database: {e}")
    finally:
        session.close()

def test_product_search():
    """Test product search functionality"""
    print("\n" + "="*50)
    print("PRODUCT SEARCH DIAGNOSTIC")
    print("="*50)
    
    session = Session()
    
    try:
        # Add test data
        print("\nAdding test data...")
        
        # Clear existing
        session.query(BranchPrice).delete()
        session.query(ChainProduct).delete()
        session.query(Branch).delete()
        session.query(Chain).delete()
        session.commit()
        
        # Add chain
        chain = Chain(name='test_chain', display_name='Test Chain')
        session.add(chain)
        session.commit()
        
        # Add branch
        branch = Branch(
            chain_id=chain.chain_id,
            store_id='001',
            name='Test Store',
            address='Test Address',
            city='תל אביב'
        )
        session.add(branch)
        session.commit()
        
        # Add product
        product = ChainProduct(
            chain_id=chain.chain_id,
            barcode='1234567890',
            name='חלב טסט'
        )
        session.add(product)
        session.commit()
        
        # Add price
        price = BranchPrice(
            chain_product_id=product.chain_product_id,
            branch_id=branch.branch_id,
            price=10.50
        )
        session.add(price)
        session.commit()
        
        print("Test data added successfully")
        
        # Test search service
        print("\nTesting ProductSearchService...")
        search_service = ProductSearchService(session)
        
        # Test 1: Search products
        print("\nTest 1: Searching for 'חלב'...")
        results = search_service.search_products_with_prices('חלב', 'תל אביב', limit=10)
        print(f"Found {len(results)} products")
        for result in results:
            print(f"  - {result['name']} ({result['barcode']})")
        
        # Test 2: Get by barcode
        print("\nTest 2: Getting product by barcode...")
        product_details = search_service.get_product_details_by_barcode('1234567890', 'תל אביב')
        if product_details:
            print(f"Found: {product_details['name']}")
            print(f"Available: {product_details.get('available', False)}")
        else:
            print("Product not found!")
        
        # Test 3: City matching
        print("\nTest 3: Testing city matching...")
        for test_city in ['תל אביב', 'תל-אביב', 'tel aviv', 'תל אביב - יפו']:
            branches = search_service._get_branches_in_city(test_city)
            print(f"  City '{test_city}' -> Found {len(branches)} branches")
        
    except Exception as e:
        print(f"\nERROR in product search: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

def test_api_endpoints():
    """Test API endpoints directly"""
    print("\n" + "="*50)
    print("API ENDPOINT DIAGNOSTIC")
    print("="*50)
    
    from fastapi.testclient import TestClient
    from main import app
    
    # Override DB for testing
    from database.connection import get_db_session
    
    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    with TestClient(app) as client:
        # Test search endpoint
        print("\nTesting /api/products/search...")
        response = client.get("/api/products/search?query=חלב&city=תל אביב")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Test barcode endpoint
        print("\nTesting /api/products/barcode/1234567890...")
        response = client.get("/api/products/barcode/1234567890?city=תל אביב")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

if __name__ == "__main__":
    print("Starting diagnostics...")
    diagnose_database()
    test_product_search()
    test_api_endpoints()
    print("\nDiagnostics complete!")
