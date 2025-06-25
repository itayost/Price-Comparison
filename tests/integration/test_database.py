"""
Integration tests for database operations.

Tests database transactions, relationships, and data integrity.
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import json

from database.new_models import (
    Chain, Branch, Product, ChainProduct, BranchPrice, 
    User, SavedCart, ComparisonHistory
)
from services.auth_service import AuthService
from services.cart_comparison_service import CartComparisonService
from tests.fixtures.sample_products import create_test_database_data


class TestDatabaseIntegration:
    """Test database operations and integrity"""
    
    def test_cascade_delete_chain(self, db_session: Session):
        """Test that deleting a chain cascades properly"""
        # Create chain with related data
        chain = Chain(name='test_chain', display_name='Test Chain')
        db_session.add(chain)
        db_session.commit()
        
        # Add branches
        branch1 = Branch(
            chain_id=chain.chain_id,
            store_id='001',
            name='Branch 1',
            address='Address 1',
            city='City 1'
        )
        branch2 = Branch(
            chain_id=chain.chain_id,
            store_id='002',
            name='Branch 2',
            address='Address 2',
            city='City 2'
        )
        db_session.add_all([branch1, branch2])
        
        # Add products
        product1 = ChainProduct(
            chain_id=chain.chain_id,
            barcode='1234567890',
            name='Product 1'
        )
        db_session.add(product1)
        db_session.commit()
        
        # Add prices
        price1 = BranchPrice(
            chain_product_id=product1.chain_product_id,
            branch_id=branch1.branch_id,
            price=10.50
        )
        db_session.add(price1)
        db_session.commit()
        
        # Delete chain
        db_session.delete(chain)
        db_session.commit()
        
        # Verify cascade
        assert db_session.query(Branch).filter_by(chain_id=chain.chain_id).count() == 0
        assert db_session.query(ChainProduct).filter_by(chain_id=chain.chain_id).count() == 0
        assert db_session.query(BranchPrice).filter_by(branch_id=branch1.branch_id).count() == 0
    
    def test_transaction_rollback(self, db_session: Session):
        """Test database transaction rollback on error"""
        initial_count = db_session.query(User).count()
        
        try:
            # Start a transaction
            user1 = User(email='user1@example.com', password_hash='hash1')
            user2 = User(email='user2@example.com', password_hash='hash2')
            user3 = User(email='user1@example.com', password_hash='hash3')  # Duplicate email
            
            db_session.add_all([user1, user2, user3])
            db_session.commit()  # This should fail
            
        except IntegrityError:
            db_session.rollback()
        
        # Verify no users were added
        final_count = db_session.query(User).count()
        assert final_count == initial_count
    
    def test_bulk_insert_performance(self, db_session: Session):
        """Test bulk insert operations"""
        # Create chain
        chain = Chain(name='bulk_test', display_name='Bulk Test')
        db_session.add(chain)
        db_session.commit()
        
        # Bulk insert products
        products = []
        for i in range(1000):
            products.append(ChainProduct(
                chain_id=chain.chain_id,
                barcode=f'BULK{i:06d}',
                name=f'Bulk Product {i}'
            ))
        
        start_time = datetime.utcnow()
        db_session.bulk_save_objects(products)
        db_session.commit()
        end_time = datetime.utcnow()
        
        # Verify all inserted
        count = db_session.query(ChainProduct).filter_by(chain_id=chain.chain_id).count()
        assert count == 1000
        
        # Check performance (should be fast)
        duration = (end_time - start_time).total_seconds()
        assert duration < 5.0  # Should complete within 5 seconds
    
    def test_complex_query_relationships(self, db_session: Session, test_prices: dict):
        """Test complex queries with multiple joins"""
        # Find all products available in Tel Aviv under 10 NIS
        query = db_session.query(ChainProduct).join(
            BranchPrice
        ).join(
            Branch
        ).filter(
            Branch.city == 'תל אביב',
            BranchPrice.price < 10.0
        ).distinct()
        
        results = query.all()
        assert len(results) > 0
        
        # Verify each result
        for product in results:
            # Check that product has prices in Tel Aviv under 10
            tel_aviv_prices = [
                price for price in product.branch_prices
                if price.branch.city == 'תל אביב' and price.price < 10.0
            ]
            assert len(tel_aviv_prices) > 0
    
    def test_saved_cart_json_integrity(self, db_session: Session, test_user: User):
        """Test JSON storage and retrieval in saved carts"""
        # Create cart with complex items
        items = [
            {
                'barcode': '7290000000001',
                'quantity': 2,
                'name': 'חלב טרה 3%',
                'notes': 'מועדף',
                'tags': ['dairy', 'essential']
            },
            {
                'barcode': '7290000000002',
                'quantity': 1,
                'name': 'לחם אחיד',
                'special_chars': 'test@#$%^&*()'
            }
        ]
        
        cart = SavedCart(
            user_id=test_user.user_id,
            cart_name='JSON Test Cart',
            city='תל אביב',
            items=json.dumps(items, ensure_ascii=False)
        )
        db_session.add(cart)
        db_session.commit()
        
        # Retrieve and verify
        saved_cart = db_session.query(SavedCart).filter_by(
            cart_id=cart.cart_id
        ).first()
        
        retrieved_items = json.loads(saved_cart.items)
        assert len(retrieved_items) == 2
        assert retrieved_items[0]['name'] == 'חלב טרה 3%'
        assert retrieved_items[0]['tags'] == ['dairy', 'essential']
        assert retrieved_items[1]['special_chars'] == 'test@#$%^&*()'
    
    def test_concurrent_price_updates(self, db_session: Session, test_prices: dict):
        """Test handling concurrent price updates"""
        # Get a price record
        price = db_session.query(BranchPrice).first()
        original_price = price.price
        
        # Simulate concurrent updates
        # Session 1
        price1 = db_session.query(BranchPrice).filter_by(
            price_id=price.price_id
        ).first()
        price1.price = 15.50
        
        # Session 2 (simulated with new query)
        price2 = db_session.query(BranchPrice).filter_by(
            price_id=price.price_id
        ).first()
        price2.price = 16.50
        
        # Commit both (last one wins)
        db_session.commit()
        
        # Verify final state
        final_price = db_session.query(BranchPrice).filter_by(
            price_id=price.price_id
        ).first()
        assert final_price.price == 16.50
    
    def test_database_constraints(self, db_session: Session):
        """Test database constraints are enforced"""
        # Test unique constraint on chain name
        chain1 = Chain(name='unique_test', display_name='Test 1')
        chain2 = Chain(name='unique_test', display_name='Test 2')
        
        db_session.add(chain1)
        db_session.commit()
        
        db_session.add(chain2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
        
        # Test foreign key constraint
        with pytest.raises(IntegrityError):
            invalid_branch = Branch(
                chain_id=99999,  # Non-existent chain
                store_id='001',
                name='Invalid Branch',
                address='Address',
                city='City'
            )
            db_session.add(invalid_branch)
            db_session.commit()
        db_session.rollback()
        
        # Test NOT NULL constraints
        with pytest.raises(IntegrityError):
            invalid_user = User(
                email=None,  # Required field
                password_hash='hash'
            )
            db_session.add(invalid_user)
            db_session.commit()
        db_session.rollback()
    
    def test_data_migration_scenario(self, db_session: Session):
        """Test a data migration scenario"""
        # Create old format data
        chain = Chain(name='migration_test', display_name='Migration Test')
        db_session.add(chain)
        db_session.commit()
        
        # Add products with old naming convention
        old_products = []
        for i in range(10):
            product = ChainProduct(
                chain_id=chain.chain_id,
                barcode=f'OLD{i:04d}',
                name=f'Old Product {i}'
            )
            old_products.append(product)
        
        db_session.add_all(old_products)
        db_session.commit()
        
        # Simulate migration - update all product names
        updated_count = db_session.query(ChainProduct).filter(
            ChainProduct.chain_id == chain.chain_id
        ).update(
            {ChainProduct.name: ChainProduct.name + ' (Updated)'},
            synchronize_session=False
        )
        db_session.commit()
        
        assert updated_count == 10
        
        # Verify migration
        migrated_products = db_session.query(ChainProduct).filter_by(
            chain_id=chain.chain_id
        ).all()
        
        for product in migrated_products:
            assert '(Updated)' in product.name
    
    def test_search_index_simulation(self, db_session: Session):
        """Test searching with database indexes"""
        # Create test data
        create_test_database_data(db_session)
        
        # Test barcode index search
        start_time = datetime.utcnow()
        result = db_session.query(ChainProduct).filter_by(
            barcode='7290000000001'
        ).all()
        barcode_search_time = (datetime.utcnow() - start_time).total_seconds()
        
        assert len(result) > 0
        assert barcode_search_time < 0.1  # Should be very fast with index
        
        # Test city search (should use index on branches)
        start_time = datetime.utcnow()
        branches = db_session.query(Branch).filter_by(
            city='תל אביב'
        ).all()
        city_search_time = (datetime.utcnow() - start_time).total_seconds()
        
        assert len(branches) > 0
        assert city_search_time < 0.1
    
    def test_orphaned_data_cleanup(self, db_session: Session):
        """Test cleanup of orphaned data"""
        # Create user with saved cart
        user = User(email='cleanup@example.com', password_hash='hash')
        db_session.add(user)
        db_session.commit()
        
        cart = SavedCart(
            user_id=user.user_id,
            cart_name='Cart to Orphan',
            city='תל אביב',
            items='[]'
        )
        db_session.add(cart)
        db_session.commit()
        
        cart_id = cart.cart_id
        
        # Delete user (should cascade to cart)
        db_session.delete(user)
        db_session.commit()
        
        # Verify cart is deleted
        orphaned_cart = db_session.query(SavedCart).filter_by(
            cart_id=cart_id
        ).first()
        assert orphaned_cart is None
    
    def test_full_text_search_hebrew(self, db_session: Session, test_products: dict):
        """Test Hebrew text search capabilities"""
        # Search for products containing Hebrew text
        search_terms = ['חלב', 'לחם', 'ביצים']
        
        for term in search_terms:
            # Using LIKE for basic text search
            results = db_session.query(ChainProduct).filter(
                ChainProduct.name.like(f'%{term}%')
            ).all()
            
            assert len(results) > 0
            
            # Verify results contain search term
            for product in results:
                assert term in product.name
    
    def test_database_backup_restore_simulation(self, db_session: Session):
        """Simulate backup and restore scenario"""
        # Create snapshot of current data
        chains_count = db_session.query(Chain).count()
        branches_count = db_session.query(Branch).count()
        products_count = db_session.query(ChainProduct).count()
        users_count = db_session.query(User).count()
        
        # Add new data
        new_chain = Chain(name='backup_test', display_name='Backup Test')
        db_session.add(new_chain)
        db_session.commit()
        
        # Verify new data exists
        assert db_session.query(Chain).filter_by(name='backup_test').first() is not None
        
        # Simulate restore by deleting new data
        db_session.delete(new_chain)
        db_session.commit()
        
        # Verify counts match original
        assert db_session.query(Chain).count() == chains_count
        assert db_session.query(Branch).count() == branches_count
        assert db_session.query(ChainProduct).count() == products_count
        assert db_session.query(User).count() == users_count
