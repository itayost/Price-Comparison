# tests/test_parsers.py
import pytest
from parsers.shufersal_parser import ShufersalParser
from parsers.victory_parser import VictoryParser

def test_shufersal_parser_store_data():
    """Test Shufersal store XML parsing"""
    parser = ShufersalParser()
    
    # Sample XML that mimics Shufersal format
    sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <root xmlns:asx="http://www.sap.com/abapxml">
        <STORES>
            <STORE>
                <STOREID>001</STOREID>
                <STORENAME>Test Store</STORENAME>
                <ADDRESS>Test Address 123</ADDRESS>
                <CITY>Tel Aviv</CITY>
            </STORE>
        </STORES>
    </root>"""
    
    stores = parser.parse_store_data(sample_xml)
    assert len(stores) == 1
    assert stores[0]["store_id"] == "1"  # Leading zeros removed
    assert stores[0]["name"] == "Test Store"

def test_victory_parser_price_data():
    """Test Victory price XML parsing"""
    parser = VictoryParser()
    
    # Sample XML that mimics Victory format
    sample_xml = b"""<?xml version="1.0" encoding="utf-8"?>
    <root>
        <StoreID>001</StoreID>
        <Product>
            <ItemCode>7290000000001</ItemCode>
            <ItemName>Test Product</ItemName>
            <ItemPrice>10.50</ItemPrice>
        </Product>
    </root>"""
    
    prices = parser.parse_price_data(sample_xml)
    assert len(prices) == 1
    assert prices[0]["barcode"] == "7290000000001"
    assert prices[0]["price"] == 10.50

def test_parser_handles_invalid_xml():
    """Test parsers handle corrupted data gracefully"""
    parser = ShufersalParser()
    
    invalid_xml = b"This is not valid XML"
    stores = parser.parse_store_data(invalid_xml)
    assert stores == []  # Should return empty list, not crash
