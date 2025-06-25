"""
Unit tests for cart comparison service.

Tests the cart comparison logic, price calculations, and store recommendations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict

from services.cart_comparison_service import CartComparisonService
from database.new_models import Chain, Branch, ChainProduct, BranchPrice
from sqlalchemy.orm import Session


class TestCartComparisonService:
    """Test CartComparisonService functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_db = Mock(spec=Session)
        self.cart_service = CartComparisonService(self.mock_db)
        
        # Create mock chains
        self.mock_chains = {
            'shufersal': Mock(chain_id=1, name='shufersal', display_name='שופרסל'),
            'victory': Mock(chain_id=2, name='victory', display_name='ויקטורי')
        }
        
        # Create mock branches
        self.mock_branches = {
            'shufersal_tlv': Mock(
                branch_id=1,
                chain_id=1,
                store_id='001',
                name='שופרסל דיזנגוף',
                address='דיזנגוף 50',
                city='תל אביב',
                chain=self.mock_chains['shufersal']
            ),
            'victory_tlv': Mock(
                branch_id=2,
                chain_id=2,
                store_id='001',
                name='ויקטורי סנטר',
                address='דיזנגוף סנטר',
                city='תל אביב',
                chain=self.mock_chains['victory']
            )
        }
    
    def test_compare_cart_single_store_cheaper(self):
        """Test cart comparison where one store is clearly cheaper"""
        cart_items = [
            {'barcode': '7290000000001', 'quantity': 2},
            {'barcode': '7290000000002', 'quantity': 1}
        ]
        city = 'תל אביב'
        
        # Mock branch query
        self.mock_db.query().filter().all.return_value = list(self.mock_branches.values())
        
        # Mock price queries
        # Shufersal prices: milk=5.90, bread=7.50
        # Victory prices: milk=6.20, bread=6.90
        self._setup_price_mocks([
            (self.mock_branches['shufersal_tlv'].branch_id, '7290000000001', 5.90, 'חלב טרה 3%'),
            (self.mock_branches['shufersal_tlv'].branch_id, '7290000000002', 7.50, 'לחם אחיד'),
            (self.mock_branches['victory_tlv'].branch_id, '7290000000001', 6.20, 'חלב טרה 3%'),
            (self.mock_branches['victory_tlv'].branch_id, '7290000000002', 6.90, 'לחם אחיד')
        ])
        
        # Compare cart
        result = self.cart_service.compare_cart(cart_items, city)
        
        # Assertions
        assert result['success'] is True
        assert result['total_items'] == 2
        assert result['cheapest_store'] is not None
        
        # Victory should be cheaper: (6.20*2 + 6.90) = 19.30 vs Shufersal (5.90*2 + 7.50) = 19.30
        # Actually they're equal, but let's adjust to make Victory cheaper
        self._setup_price_mocks([
            (self.mock_branches['shufersal_tlv'].branch_id, '7290000000001', 5.90, 'חלב טרה 3%'),
            (self.mock_branches['shufersal_tlv'].branch_id, '7290000000002', 7.50, 'לחם אחיד'),
            (self.mock_branches['victory_tlv'].branch_id, '7290000000001', 5.50, 'חלב טרה 3%'),
            (self.mock_branches['victory_tlv'].branch_id, '7290000000002', 6.90, 'לחם אחיד')
        ])
        
        result = self.cart_service.compare_cart(cart_items, city)
        assert result['cheapest_store']['chain_name'] == 'victory'
        assert result['cheapest_store']['total_price'] == 17.90  # (5.50*2 + 6.90)
    
    def test_compare_cart_with_missing_products(self):
        """Test cart comparison when some products are missing in stores"""
        cart_items = [
            {'barcode': '7290000000001', 'quantity': 1},
            {'barcode': '7290000000999', 'quantity': 1}  # Non-existent product
        ]
        city = 'תל אביב'
        
        # Mock branch query
        self.mock_db.query().filter().all.return_value = list(self.mock_branches.values())
        
        # Only product 001 exists
        self._setup_price_mocks([
            (self.mock_branches['shufersal_tlv'].branch_id, '7290000000001', 5.90, 'חלב טרה 3%'),
            (self.mock_branches['victory_tlv'].branch_id, '7290000000001', 6.20, 'חלב טרה 3%')
        ])
        
        result = self.cart_service.compare_cart(cart_items, city)
        
        assert result['success'] is True
        assert result['cheapest_store'] is not None
        assert result['cheapest_store']['available_items'] == 1
        assert result['cheapest_store']['missing_items'] == 1
        assert len(result['cheapest_store']['missing_products']) == 1
        assert result['cheapest_store']['missing_products'][0] == '7290000000999'
    
    def test_compare_cart_empty_city(self):
        """Test cart comparison with no stores in the city"""
        cart_items = [{'barcode': '7290000000001', 'quantity': 1}]
        city = 'עיר לא קיימת'
        
        # Mock no branches found
        self.mock_db.query().filter().all.return_value = []
        
        result = self.cart_service.compare_cart(cart_items, city)
        
        assert result['success'] is False
        assert result['cheapest_store'] is None
        assert len(result['all_stores']) == 0
        assert 'message' in result
    
    def test_compare_cart_empty_cart(self):
        """Test comparison with empty cart"""
        cart_items = []
        city = 'תל אביב'
        
        result = self.cart_service.compare_cart(cart_items, city)
        
        assert result['success'] is False
        assert 'message' in result
        assert 'empty' in result['message'].lower()
    
    def test_calculate_store_prices(self):
        """Test internal price calculation method"""
        # Setup test data
        branch = self.mock_branches['shufersal_tlv']
        cart_items = [
            {'barcode': '7290000000001', 'quantity': 2},
            {'barcode': '7290000000002', 'quantity': 3}
        ]
        
        # Mock prices
        mock_prices = {
            '7290000000001': Mock(price=5.90, chain_product=Mock(name='חלב')),
            '7290000000002': Mock(price=7.50, chain_product=Mock(name='לחם'))
        }
        
        # Calculate
        result = self.cart_service._calculate_store_prices(branch, cart_items, mock_prices)
        
        assert result['total_price'] == (5.90 * 2) + (7.50 * 3)  # 34.30
        assert result['available_items'] == 2
        assert result['missing_items'] == 0
        assert len(result['items']) == 2
        
        # Check individual items
        milk_item = next(item for item in result['items'] if item['barcode'] == '7290000000001')
        assert milk_item['quantity'] == 2
        assert milk_item['unit_price'] == 5.90
        assert milk_item['total_price'] == 11.80
    
    def test_normalize_city_name(self):
        """Test city name normalization"""
        test_cases = [
            ('תל אביב', 'תל אביב'),
            ('תל-אביב', 'תל אביב'),
            ('תל אביב - יפו', 'תל אביב יפו'),
            ('חיפה  ', 'חיפה'),
            ('  ירושלים', 'ירושלים'),
            ('TEL AVIV', 'tel aviv'),
            ('Tel-Aviv', 'tel aviv')
        ]
        
        for input_city, expected in test_cases:
            normalized = self.cart_service._normalize_city_name(input_city)
            assert normalized == expected
    
    def test_filter_branches_by_chain(self):
        """Test filtering branches by chain preference"""
        cart_items = [{'barcode': '7290000000001', 'quantity': 1}]
        city = 'תל אביב'
        chain_filter = 'shufersal'
        
        # Mock only Shufersal branch
        self.mock_db.query().filter().all.return_value = [self.mock_branches['shufersal_tlv']]
        
        # Mock price
        self._setup_price_mocks([
            (self.mock_branches['shufersal_tlv'].branch_id, '7290000000001', 5.90, 'חלב')
        ])
        
        result = self.cart_service.compare_cart(cart_items, city, chain_filter)
        
        assert result['success'] is True
        assert len(result['all_stores']) == 1
        assert result['all_stores'][0]['chain_name'] == 'shufersal'
    
    def test_save_comparison_to_history(self):
        """Test saving comparison results to history"""
        user_id = 123
        comparison_result = {
            'success': True,
            'cheapest_store': {
                'chain_name': 'victory',
                'branch_name': 'ויקטורי סנטר',
                'total_price': 45.60
            },
            'all_stores': [
                {'chain_name': 'victory', 'total_price': 45.60},
                {'chain_name': 'shufersal', 'total_price': 48.90}
            ]
        }
        
        # Mock save operation
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        
        # Save to history
        history = self.cart_service.save_comparison_to_history(user_id, comparison_result)
        
        assert history is not None
        assert history.user_id == user_id
        assert history.cheapest_chain == 'victory'
        assert history.cheapest_price == 45.60
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
    
    def test_get_price_trends(self):
        """Test getting price trends for products"""
        barcodes = ['7290000000001', '7290000000002']
        days = 7
        
        # Mock historical price data
        mock_history = [
            Mock(barcode='7290000000001', price=5.90, date=datetime(2025, 1, 1)),
            Mock(barcode='7290000000001', price=6.20, date=datetime(2025, 1, 2)),
            Mock(barcode='7290000000001', price=5.50, date=datetime(2025, 1, 3)),
            Mock(barcode='7290000000002', price=7.50, date=datetime(2025, 1, 1)),
            Mock(barcode='7290000000002', price=7.50, date=datetime(2025, 1, 2)),
            Mock(barcode='7290000000002', price=6.90, date=datetime(2025, 1, 3))
        ]
        
        self.mock_db.query().filter().all.return_value = mock_history
        
        trends = self.cart_service.get_price_trends(barcodes, days)
        
        assert '7290000000001' in trends
        assert '7290000000002' in trends
        assert len(trends['7290000000001']) == 3
        assert trends['7290000000001'][0]['price'] == 5.90
        assert trends['7290000000002'][-1]['price'] == 6.90
    
    # Helper methods
    def _setup_price_mocks(self, price_data: List[tuple]):
        """Helper to setup price query mocks"""
        price_mocks = []
        
        for branch_id, barcode, price, name in price_data:
            mock_price = Mock(
                branch_id=branch_id,
                price=price,
                chain_product=Mock(
                    barcode=barcode,
                    name=name
                )
            )
            price_mocks.append(mock_price)
        
        # Setup the query chain for prices
        mock_query = Mock()
        mock_query.join().filter().all.return_value = price_mocks
        self.mock_db.query.return_value = mock_query
