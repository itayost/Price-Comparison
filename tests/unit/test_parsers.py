"""
Unit tests for XML parsers.

Tests the parsing of store and price data from Shufersal and Victory chains.
"""

import pytest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

from parsers.shufersal_parser import ShufersalParser
from parsers.victory_parser import VictoryParser
from tests.fixtures.sample_xmls import (
    SHUFERSAL_STORES_XML,
    SHUFERSAL_PRICES_XML,
    VICTORY_STORES_XML,
    VICTORY_PRICES_XML,
    EMPTY_STORES_XML,
    MALFORMED_XML,
    PRICE_WITH_MISSING_FIELDS_XML,
    get_gzipped_xml
)


class TestShufersalParser:
    """Test Shufersal XML parser"""

    def setup_method(self):
        """Set up test fixtures"""
        self.parser = ShufersalParser()

    def test_parse_store_data_success(self):
        """Test successful parsing of Shufersal store XML"""
        stores = self.parser.parse_store_data(SHUFERSAL_STORES_XML.encode('utf-8'))

        assert len(stores) == 2

        # Check first store
        store1 = stores[0]
        assert store1['store_id'] == '1'  # Leading zeros removed
        assert store1['name'] == 'שלי ת"א- בן יהודה'
        assert store1['address'] == 'בן יהודה 79'
        assert store1['city'] == 'תל אביב'

        # Check second store
        store2 = stores[1]
        assert store2['store_id'] == '312'
        assert store2['name'] == 'דיל חיפה- קרית אליעזר'
        assert store2['address'] == 'ככר מאירהוף'
        assert store2['city'] == 'חיפה'

    def test_parse_store_data_empty(self):
        """Test parsing empty store list"""
        stores = self.parser.parse_store_data(EMPTY_STORES_XML.encode('utf-8'))
        assert len(stores) == 0

    def test_parse_store_data_malformed(self):
        """Test handling of malformed XML"""
        stores = self.parser.parse_store_data(MALFORMED_XML.encode('utf-8'))
        assert len(stores) == 0

    def test_parse_price_data_success(self):
        """Test successful parsing of Shufersal price XML"""
        prices = self.parser.parse_price_data(SHUFERSAL_PRICES_XML.encode('utf-8'))

        assert len(prices) == 3

        # Check first product (milk)
        price1 = prices[0]
        assert price1['store_id'] == '1'  # Leading zeros removed
        assert price1['barcode'] == '7290000000001'
        assert price1['name'] == 'חלב טרה 3% בקרטון 1 ליטר'
        assert price1['price'] == 5.90

        # Check second product (bread)
        price2 = prices[1]
        assert price2['barcode'] == '7290000000002'
        assert price2['name'] == 'לחם אחיד פרוס'
        assert price2['price'] == 7.50

        # Check third product (eggs)
        price3 = prices[2]
        assert price3['barcode'] == '7290000000003'
        assert price3['name'] == 'ביצים L 12 יחידות'
        assert price3['price'] == 12.90

    def test_parse_price_data_missing_fields(self):
        """Test handling of products with missing fields"""
        prices = self.parser.parse_price_data(PRICE_WITH_MISSING_FIELDS_XML.encode('utf-8'))

        # Should skip products with missing required fields
        assert len(prices) == 1  # Only the complete product
        assert prices[0]['barcode'] == '7290000001000'
        assert prices[0]['price'] == 15.00

    @patch('requests.get')
    def test_get_store_file_urls(self, mock_get):
        """Test scraping store file URLs from index page"""
        # Mock the HTML response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <a href="/FileObject/UpdateCategory?catID=5&storeId=1&fileName=Stores7290027600007-001-202501010600.gz">לחץ להורדה</a>
                <a href="/FileObject/UpdateCategory?catID=5&storeId=2&fileName=Stores7290027600007-002-202501010600.gz">לחץ להורדה</a>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response

        urls = self.parser.get_store_file_urls()

        assert len(urls) == 2
        assert 'Stores' in urls[0]
        assert '.gz' in urls[0]

    @patch('requests.get')
    def test_download_gz_file(self, mock_get):
        """Test downloading and extracting GZ file"""
        # Mock the response with gzipped content
        test_content = b"Test XML content"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = get_gzipped_xml("Test XML content")
        mock_get.return_value = mock_response

        result = self.parser.download_gz_file("http://test.com/file.gz")

        assert result == test_content


class TestVictoryParser:
    """Test Victory XML parser"""

    def setup_method(self):
        """Set up test fixtures"""
        self.parser = VictoryParser()

    def test_parse_store_data_success(self):
        """Test successful parsing of Victory store XML"""
        stores = self.parser.parse_store_data(VICTORY_STORES_XML.encode('utf-8'))

        assert len(stores) == 3

        # Check first store
        store1 = stores[0]
        assert store1['store_id'] == '001'
        assert store1['store_name'] == 'גן-יבנה'
        assert store1['address'] == 'הכישור 8'
        assert store1['city'] == 'גן יבנה'
        assert store1['chain_id'] == '7290696200003'
        assert store1['sub_chain_id'] == '001'

        # Check Tel Aviv store
        ta_store = next(s for s in stores if s['city'] == 'תל אביב')
        assert ta_store['store_id'] == '016'
        assert ta_store['store_name'] == 'פלורנטין'
        assert ta_store['address'] == 'סלמה 53'

    def test_parse_price_data_success(self):
        """Test successful parsing of Victory price XML"""
        prices = self.parser.parse_price_data(VICTORY_PRICES_XML.encode('utf-8'))

        assert len(prices) == 3

        # Check first product (milk)
        price1 = prices[0]
        assert price1['store_id'] == '074'
        assert price1['barcode'] == '7290000000001'
        assert price1['name'] == 'חלב טרה 3% 1 ליטר'
        assert price1['price'] == 6.20

        # Check second product (bread)
        price2 = prices[1]
        assert price2['barcode'] == '7290000000002'
        assert price2['price'] == 6.90

        # Check third product (eggs)
        price3 = prices[2]
        assert price3['barcode'] == '7290000000003'
        assert price3['price'] == 13.50

    @patch('requests.get')
    def test_get_store_file_urls_case_insensitive(self, mock_get):
        """Test that Victory parser handles case-insensitive file matching"""
        # Mock the HTML response with mixed case
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <a href="/Stores7290696200003-001-202501010600.gz">לחץ כאן להורדה</a>
                <a href="/STORES7290696200003-002-202501010600.gz">לחץ כאן להורדה</a>
                <a href="/StoresFull7290696200003-003-202501010600.gz">לחץ כאן להורדה</a>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response

        urls = self.parser.get_store_file_urls()

        assert len(urls) == 3
        # All URLs should be found despite case differences


class TestParserIntegration:
    """Test parser integration and error handling"""

    @pytest.mark.parametrize("parser_class,chain_name", [
        (ShufersalParser, 'shufersal'),
        (VictoryParser, 'victory')
    ])
    def test_parser_initialization(self, parser_class, chain_name):
        """Test that parsers initialize correctly"""
        parser = parser_class()
        assert parser.chain_name == chain_name
        assert parser.base_url is not None

    def test_hebrew_text_handling(self):
        """Test that Hebrew text is preserved correctly"""
        shufersal_parser = ShufersalParser()
        victory_parser = VictoryParser()

        # Test Shufersal Hebrew
        shufersal_stores = shufersal_parser.parse_store_data(SHUFERSAL_STORES_XML.encode('utf-8'))
        assert any('שופרסל' in store['name'] for store in shufersal_stores)

        # Test Victory Hebrew
        victory_stores = victory_parser.parse_store_data(VICTORY_STORES_XML.encode('utf-8'))
        assert any('ויקטורי' in store.get('store_name', '') for store in victory_stores)

    def test_price_validation(self):
        """Test that invalid prices are filtered out"""
        xml_with_invalid_prices = """<?xml version="1.0" encoding="utf-8"?>
        <root>
          <ChainId>7290027600007</ChainId>
          <StoreId>001</StoreId>
          <Items Count="2">
            <Item>
              <ItemCode>7290000000001</ItemCode>
              <ItemName>Product 1</ItemName>
              <ItemPrice>-5.00</ItemPrice>
            </Item>
            <Item>
              <ItemCode>7290000000002</ItemCode>
              <ItemName>Product 2</ItemName>
              <ItemPrice>0</ItemPrice>
            </Item>
          </Items>
        </root>"""

        parser = ShufersalParser()
        prices = parser.parse_price_data(xml_with_invalid_prices.encode('utf-8'))

        # Should filter out negative and zero prices
        assert len(prices) == 0

    def test_store_id_normalization(self):
        """Test that store IDs are normalized correctly (leading zeros removed)"""
        # Test Shufersal with leading zeros
        shufersal_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <asx:abap xmlns:asx="http://www.sap.com/abapxml" version="1.0">
        <asx:values>
        <CHAINID>7290027600007</CHAINID>
        <STORES>
        <STORE>
        <STOREID>001</STOREID>
        <STORENAME>Test Store</STORENAME>
        <ADDRESS>Test Address</ADDRESS>
        <CITY>Test City</CITY>
        </STORE>
        </STORES>
        </asx:values>
        </asx:abap>"""

        parser = ShufersalParser()
        stores = parser.parse_store_data(shufersal_xml.encode('utf-8'))
        assert stores[0]['store_id'] == '1'  # Leading zeros removed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
