"""
Unit tests for database models.

Tests the SQLAlchemy models and their relationships.
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.new_models import (
    Chain, Branch, Product, ChainProduct, BranchPrice, User, SavedCart
)


class TestChainModel:
    """Test Chain model"""
    
    def test_create_chain(self, db_session: Session):
        """Test creating a chain"""
        chain = Chain(
            name='test_chain',
            display_name='Test Chain'
        )
        db_session.add(chain)
        db_session.commit()
        
        assert chain.chain_id is not None
        assert chain.name == 'test_chain'
        assert chain.display_name == 'Test Chain'
    
    def test_chain_unique_name(self, db_session: Session):
        """Test that chain names must be unique"""
        chain1 = Chain(name='unique_chain', display_name='Chain 1')
        chain2 = Chain(name='unique_chain', display_name='Chain 2')
        
        db_session.add(chain1)
        db_session.commit()
        
        db_session.add(chain2)
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_chain_relationships(self, db_session: Session, test_chains: dict):
        """Test chain relationships"""
        chain = test_chains['shufersal']
        
        # Test branches relationship
        branches = chain.branches
        assert len(branches) > 0
        assert all(branch.chain_id == chain.chain_id for branch in branches)
        
        # Test chain_products relationship
        products = chain.chain_products
        assert len(products) > 0
        assert all(product.chain_id == chain.chain_id for product in products)


class TestBranchModel:
    """Test Branch model"""
    
    def test_create_branch(self, db_session: Session, test_chains: dict):
        """Test creating a branch"""
        branch = Branch(
            chain_id=test_chains['shufersal'].chain_id,
            store_id='999',
            name='Test Branch',
            address='Test Address 123',
            city='תל אביב'
        )
        db_session.add(branch)
        db_session.commit()
        
        assert branch.branch_id is not None
        assert branch.store_id == '999'
        assert branch.city == 'תל אביב'
    
    def test_branch_unique_constraint(self, db_session: Session, test_chains: dict):
        """Test that chain_id + store_id must be unique"""
        chain_id = test_chains['shufersal'].chain_id
        
        branch1 = Branch(
            chain_id=chain_id,
            store_id='123',
            name='Branch 1',
            address='Address 1',
            city='City 1'
        )
        branch2 = Branch(
            chain_id=chain_id,
            store_id='123',  # Same store_id
            name='Branch 2',
            address='Address 2',
            city='City 2'
        )
        
        db_session.add(branch1)
        db_session.commit()
        
        db_session.add(branch2)
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_branch_chain_relationship(self, db_session: Session, test_branches: dict):
        """Test branch-chain relationship"""
        branch = test_branches['shufersal_dizengoff']
        
        assert branch.chain is not None
        assert branch.chain.name == 'shufersal'


class TestProductModel:
    """Test Product model (canonical products)"""
    
    def test_create_product(self, db_session: Session):
        """Test creating a canonical product"""
        product = Product(
            canonical_name='Generic Milk 1L',
            category='dairy',
            unit_size=1.0,
            unit_type='liter'
        )
        db_session.add(product)
        db_session.commit()
        
        assert product.product_id is not None
        assert product.canonical_name == 'Generic Milk 1L'
        assert product.unit_size == 1.0
    
    def test_product_optional_fields(self, db_session: Session):
        """Test that product fields are optional"""
        product = Product(canonical_name='Test Product')
        db_session.add(product)
        db_session.commit()
        
        assert product.category is None
        assert product.unit_size is None
        assert product.unit_type is None


class TestChainProductModel:
    """Test ChainProduct model"""
    
    def test_create_chain_product(self, db_session: Session, test_chains: dict):
        """Test creating a chain-specific product"""
        chain_product = ChainProduct(
            chain_id=test_chains['shufersal'].chain_id,
            barcode='1234567890123',
            name='Test Product',
            product_id=None  # Not matched to canonical product yet
        )
        db_session.add(chain_product)
        db_session.commit()
        
        assert chain_product.chain_product_id is not None
        assert chain_product.barcode == '1234567890123'
    
    def test_chain_product_unique_constraint(self, db_session: Session, test_chains: dict):
        """Test that chain_id + barcode must be unique"""
        chain_id = test_chains['shufersal'].chain_id
        
        product1 = ChainProduct(
            chain_id=chain_id,
            barcode='7290000000999',
            name='Product 1'
        )
        product2 = ChainProduct(
            chain_id=chain_id,
            barcode='7290000000999',  # Same barcode
            name='Product 2'
        )
        
        db_session.add(product1)
        db_session.commit()
        
        db_session.add(product2)
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_chain_product_relationships(self, db_session: Session, test_products: dict):
        """Test chain product relationships"""
        product = test_products['shufersal_7290000000001']
        
        # Test chain relationship
        assert product.chain is not None
        assert product.chain.name == 'shufersal'
        
        # Test prices relationship
        assert len(product.prices) > 0


class TestBranchPriceModel:
    """Test BranchPrice model"""
    
    def test_create_price(self, db_session: Session, test_branches: dict, test_products: dict):
        """Test creating a price entry"""
        price = BranchPrice(
            chain_product_id=test_products['shufersal_7290000000001'].chain_product_id,
            branch_id=test_branches['shufersal_dizengoff'].branch_id,
            price=9.99,
            last_updated=datetime.utcnow()
        )
        db_session.add(price)
        db_session.commit()
        
        assert price.price_id is not None
        assert float(price.price) == 9.99
    
    def test_price_unique_constraint(self, db_session: Session, test_branches: dict, test_products: dict):
        """Test that chain_product_id + branch_id must be unique"""
        chain_product_id = test_products['shufersal_7290000000001'].chain_product_id
        branch_id = test_branches['shufersal_dizengoff'].branch_id
        
        price1 = BranchPrice(
            chain_product_id=chain_product_id,
            branch_id=branch_id,
            price=5.50
        )
        price2 = BranchPrice(
            chain_product_id=chain_product_id,
            branch_id=branch_id,
            price=6.50  # Different price, same product/branch
        )
        
        db_session.add(price1)
        db_session.commit()
        
        db_session.add(price2)
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_price_relationships(self, db_session: Session, test_prices: dict):
        """Test price relationships"""
        # Get any price from the test data
        price = list(test_prices.values())[0]
        
        # Test chain_product relationship
        assert price.chain_product is not None
        assert price.chain_product.barcode is not None
        
        # Test branch relationship
        assert price.branch is not None
        assert price.branch.city is not None


class TestUserModel:
    """Test User model"""
    
    def test_create_user(self, db_session: Session):
        """Test creating a user"""
        user = User(
            email='test@example.com',
            password_hash='hashed_password_here',
            created_at=datetime.utcnow()
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.user_id is not None
        assert user.email == 'test@example.com'
    
    def test_user_unique_email(self, db_session: Session):
        """Test that email must be unique"""
        user1 = User(email='unique@example.com', password_hash='hash1')
        user2 = User(email='unique@example.com', password_hash='hash2')
        
        db_session.add(user1)
        db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_user_saved_carts_relationship(self, db_session: Session, test_user: User):
        """Test user-saved carts relationship"""
        # Create a saved cart
        cart = SavedCart(
            user_id=test_user.user_id,
            cart_name='Test Cart',
            city='תל אביב',
            items='[{"barcode": "123", "quantity": 1}]'
        )
        db_session.add(cart)
        db_session.commit()
        
        # Test relationship
        assert len(test_user.saved_carts) == 1
        assert test_user.saved_carts[0].cart_name == 'Test Cart'


class TestSavedCartModel:
    """Test SavedCart model"""
    
    def test_create_saved_cart(self, db_session: Session, test_user: User):
        """Test creating a saved cart"""
        cart = SavedCart(
            user_id=test_user.user_id,
            cart_name='Weekly Shopping',
            city='תל אביב',
            items='[{"barcode": "7290000000001", "quantity": 2, "name": "חלב"}]',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(cart)
        db_session.commit()
        
        assert cart.cart_id is not None
        assert cart.cart_name == 'Weekly Shopping'
        assert cart.city == 'תל אביב'
    
    def test_saved_cart_unique_constraint(self, db_session: Session, test_user: User):
        """Test that user_id + cart_name must be unique"""
        cart1 = SavedCart(
            user_id=test_user.user_id,
            cart_name='My Cart',
            city='City 1',
            items='[]'
        )
        cart2 = SavedCart(
            user_id=test_user.user_id,
            cart_name='My Cart',  # Same name
            city='City 2',
            items='[]'
        )
        
        db_session.add(cart1)
        db_session.commit()
        
        db_session.add(cart2)
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_saved_cart_user_relationship(self, db_session: Session, test_user: User):
        """Test saved cart-user relationship"""
        cart = SavedCart(
            user_id=test_user.user_id,
            cart_name='Test Cart',
            city='תל אביב',
            items='[]'
        )
        db_session.add(cart)
        db_session.commit()
        
        assert cart.user is not None
        assert cart.user.email == test_user.email


class TestModelCascadeDeletes:
    """Test cascade delete behavior"""
    
    def test_chain_cascade_delete(self, db_session: Session):
        """Test that deleting a chain deletes related records"""
        # Create chain with related data
        chain = Chain(name='cascade_test', display_name='Cascade Test')
        db_session.add(chain)
        db_session.commit()
        
        branch = Branch(
            chain_id=chain.chain_id,
            store_id='001',
            name='Test Branch',
            address='Test',
            city='Test'
        )
        product = ChainProduct(
            chain_id=chain.chain_id,
            barcode='123',
            name='Test Product'
        )
        db_session.add_all([branch, product])
        db_session.commit()
        
        # Delete chain
        db_session.delete(chain)
        db_session.commit()
        
        # Verify cascades
        assert db_session.query(Branch).filter_by(branch_id=branch.branch_id).first() is None
        assert db_session.query(ChainProduct).filter_by(chain_product_id=product.chain_product_id).first() is None
    
    def test_user_cascade_delete(self, db_session: Session):
        """Test that deleting a user deletes their saved carts"""
        user = User(email='cascade@test.com', password_hash='test')
        db_session.add(user)
        db_session.commit()
        
        cart = SavedCart(
            user_id=user.user_id,
            cart_name='Test Cart',
            city='Test',
            items='[]'
        )
        db_session.add(cart)
        db_session.commit()
        
        # Delete user
        db_session.delete(user)
        db_session.commit()
        
        # Verify cascade
        assert db_session.query(SavedCart).filter_by(cart_id=cart.cart_id).first() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
