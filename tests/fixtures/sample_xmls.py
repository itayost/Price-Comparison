"""
Sample XML responses for testing parsers.

Based on real XML structures from Israeli supermarket chains.
"""

# Victory store XML - Real structure
VICTORY_STORES_XML = """<?xml version="1.0" encoding="utf-8"?>
<Store Date="25/06/25" Time="06:00:04">
  <Branches>
    <Branch>
      <ChainID>7290696200003</ChainID>
      <SubChainID>001</SubChainID>
      <StoreID>001</StoreID>
      <BikoretNo />
      <StoreType>1</StoreType>
      <ChainName>ויקטורי</ChainName>
      <SubChainName>ויקטורי</SubChainName>
      <StoreName>גן-יבנה</StoreName>
      <Address>הכישור 8</Address>
      <City>גן יבנה</City>
      <ZIPCode>7080000</ZIPCode>
      <LastUpdateDate>25/07/2022 09:55:14</LastUpdateDate>
      <Latitude />
      <Longitude />
    </Branch>
    <Branch>
      <ChainID>7290696200003</ChainID>
      <SubChainID>001</SubChainID>
      <StoreID>016</StoreID>
      <BikoretNo />
      <StoreType>1</StoreType>
      <ChainName>ויקטורי</ChainName>
      <SubChainName>ויקטורי</SubChainName>
      <StoreName>פלורנטין</StoreName>
      <Address>סלמה 53</Address>
      <City>תל אביב</City>
      <ZIPCode>6606034</ZIPCode>
      <LastUpdateDate>16/04/2015 13:11:24</LastUpdateDate>
      <Latitude />
      <Longitude />
    </Branch>
    <Branch>
      <ChainID>7290696200003</ChainID>
      <SubChainID>001</SubChainID>
      <StoreID>027</StoreID>
      <BikoretNo />
      <StoreType>1</StoreType>
      <ChainName>ויקטורי</ChainName>
      <SubChainName>ויקטורי</SubChainName>
      <StoreName>שער העליה</StoreName>
      <Address>שלוסברג 1</Address>
      <City>חיפה</City>
      <ZIPCode>3584001</ZIPCode>
      <LastUpdateDate>27/07/2022 09:59:19</LastUpdateDate>
      <Latitude />
      <Longitude />
    </Branch>
  </Branches>
</Store>"""

# Victory price XML - Real structure
VICTORY_PRICES_XML = """<?xml version="1.0" encoding="utf-8"?>
<Prices>
  <ChainID>7290696200003</ChainID>
  <SubChainID>001</SubChainID>
  <StoreID>074</StoreID>
  <BikoretNo>000</BikoretNo>
  <Products>
    <Product>
      <PriceUpdateDate>2025/05/19 06:21</PriceUpdateDate>
      <ItemCode>7290000000001</ItemCode>
      <ItemType>1</ItemType>
      <ItemName>חלב טרה 3% 1 ליטר</ItemName>
      <ManufactureName>טרה</ManufactureName>
      <ManufactureCountry />
      <ManufactureItemDescription />
      <UnitQty>יח`</UnitQty>
      <Quantity>1</Quantity>
      <UnitMeasure />
      <BisWeighted>0</BisWeighted>
      <QtyInPackage>1</QtyInPackage>
      <ItemPrice>6.20</ItemPrice>
      <UnitOfMeasurePrice>6.20</UnitOfMeasurePrice>
      <AllowDiscount>1</AllowDiscount>
      <itemStatus>1</itemStatus>
      <LastUpdateDate />
      <LastUpdateTime />
    </Product>
    <Product>
      <PriceUpdateDate>2025/06/16 07:35</PriceUpdateDate>
      <ItemCode>7290000000002</ItemCode>
      <ItemType>1</ItemType>
      <ItemName>לחם אחיד פרוס</ItemName>
      <ManufactureName>ברמן</ManufactureName>
      <ManufactureCountry />
      <ManufactureItemDescription />
      <UnitQty>יח`</UnitQty>
      <Quantity>1</Quantity>
      <UnitMeasure />
      <BisWeighted>0</BisWeighted>
      <QtyInPackage>1</QtyInPackage>
      <ItemPrice>6.90</ItemPrice>
      <UnitOfMeasurePrice>6.90</UnitOfMeasurePrice>
      <AllowDiscount>1</AllowDiscount>
      <itemStatus>1</itemStatus>
      <LastUpdateDate />
      <LastUpdateTime />
    </Product>
    <Product>
      <PriceUpdateDate>2025/03/27 13:15</PriceUpdateDate>
      <ItemCode>7290000000003</ItemCode>
      <ItemType>1</ItemType>
      <ItemName>ביצים L 12 יחידות</ItemName>
      <ManufactureName>משק כהן</ManufactureName>
      <ManufactureCountry />
      <ManufactureItemDescription />
      <UnitQty>יח`</UnitQty>
      <Quantity>12</Quantity>
      <UnitMeasure />
      <BisWeighted>0</BisWeighted>
      <QtyInPackage>12</QtyInPackage>
      <ItemPrice>13.50</ItemPrice>
      <UnitOfMeasurePrice>1.13</UnitOfMeasurePrice>
      <AllowDiscount>1</AllowDiscount>
      <itemStatus>1</itemStatus>
      <LastUpdateDate />
      <LastUpdateTime />
    </Product>
  </Products>
</Prices>"""

# Shufersal store XML - Real structure
SHUFERSAL_STORES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<asx:abap xmlns:asx="http://www.sap.com/abapxml" version="1.0">
<asx:values>
<CHAINID>7290027600007</CHAINID>
<STORES>
<STORE>
<SUBCHAINID>1</SUBCHAINID>
<STOREID>1</STOREID>
<BIKORETNO>7</BIKORETNO>
<STORETYPE>1</STORETYPE>
<CHAINNAME>שופרסל</CHAINNAME>
<SUBCHAINNAME>שופרסל שלי</SUBCHAINNAME>
<STORENAME>שלי ת"א- בן יהודה</STORENAME>
<ADDRESS>בן יהודה 79</ADDRESS>
<CITY>תל אביב</CITY>
<ZIPCODE>6343504</ZIPCODE>
</STORE>
<STORE>
<SUBCHAINID>2</SUBCHAINID>
<STOREID>312</STOREID>
<BIKORETNO>7</BIKORETNO>
<STORETYPE>1</STORETYPE>
<CHAINNAME>שופרסל</CHAINNAME>
<SUBCHAINNAME>שופרסל דיל</SUBCHAINNAME>
<STORENAME>דיל חיפה- קרית אליעזר</STORENAME>
<ADDRESS>ככר מאירהוף</ADDRESS>
<CITY>חיפה</CITY>
<ZIPCODE>35154</ZIPCODE>
</STORE>
</STORES>
</asx:values>
</asx:abap>"""

# Shufersal price XML - Real structure
SHUFERSAL_PRICES_XML = """<?xml version="1.0" encoding="utf-8"?>
<root>
  <ChainId>7290027600007</ChainId>
  <SubChainId>001</SubChainId>
  <StoreId>001</StoreId>
  <BikoretNo>9</BikoretNo>
  <DllVerNo>8.0.1.3</DllVerNo>
  <Items Count="5172">
    <Item>
      <PriceUpdateDate>2025-01-08 11:16</PriceUpdateDate>
      <ItemCode>7290000000001</ItemCode>
      <ItemType>1</ItemType>
      <ItemName>חלב טרה 3% בקרטון 1 ליטר</ItemName>
      <ManufacturerName>טרה</ManufacturerName>
      <ManufactureCountry>IL</ManufactureCountry>
      <ManufacturerItemDescription>חלב טרה 3% בקרטון 1 ליטר</ManufacturerItemDescription>
      <UnitQty>ליטר</UnitQty>
      <Quantity>1.00</Quantity>
      <bIsWeighted>0</bIsWeighted>
      <UnitOfMeasure>ליטר</UnitOfMeasure>
      <QtyInPackage>1</QtyInPackage>
      <ItemPrice>5.90</ItemPrice>
      <UnitOfMeasurePrice>5.90</UnitOfMeasurePrice>
      <AllowDiscount>1</AllowDiscount>
      <ItemStatus>1</ItemStatus>
    </Item>
    <Item>
      <PriceUpdateDate>2025-01-08 11:16</PriceUpdateDate>
      <ItemCode>7290000000002</ItemCode>
      <ItemType>1</ItemType>
      <ItemName>לחם אחיד פרוס</ItemName>
      <ManufacturerName>ברמן</ManufacturerName>
      <ManufactureCountry>IL</ManufactureCountry>
      <ManufacturerItemDescription>לחם אחיד פרוס</ManufacturerItemDescription>
      <UnitQty>יחידה</UnitQty>
      <Quantity>1.00</Quantity>
      <bIsWeighted>0</bIsWeighted>
      <UnitOfMeasure>יחידה</UnitOfMeasure>
      <QtyInPackage>1</QtyInPackage>
      <ItemPrice>7.50</ItemPrice>
      <UnitOfMeasurePrice>7.50</UnitOfMeasurePrice>
      <AllowDiscount>1</AllowDiscount>
      <ItemStatus>1</ItemStatus>
    </Item>
    <Item>
      <PriceUpdateDate>2025-01-08 11:16</PriceUpdateDate>
      <ItemCode>7290000000003</ItemCode>
      <ItemType>1</ItemType>
      <ItemName>ביצים L 12 יחידות</ItemName>
      <ManufacturerName>משק כהן</ManufacturerName>
      <ManufactureCountry>IL</ManufactureCountry>
      <ManufacturerItemDescription>ביצים L 12 יחידות</ManufacturerItemDescription>
      <UnitQty>יחידה</UnitQty>
      <Quantity>12.00</Quantity>
      <bIsWeighted>0</bIsWeighted>
      <UnitOfMeasure>תריסר</UnitOfMeasure>
      <QtyInPackage>12</QtyInPackage>
      <ItemPrice>12.90</ItemPrice>
      <UnitOfMeasurePrice>1.08</UnitOfMeasurePrice>
      <AllowDiscount>1</AllowDiscount>
      <ItemStatus>1</ItemStatus>
    </Item>
  </Items>
</root>"""

# Edge cases for testing
EMPTY_STORES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<asx:abap xmlns:asx="http://www.sap.com/abapxml" version="1.0">
<asx:values>
<CHAINID>7290027600007</CHAINID>
<STORES>
</STORES>
</asx:values>
</asx:abap>"""

MALFORMED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<root>
    <ChainId>7290027600007
    <StoreId>001</StoreId>
    <!-- Missing closing tag and other issues -->
</root>"""

PRICE_WITH_MISSING_FIELDS_XML = """<?xml version="1.0" encoding="utf-8"?>
<root>
  <ChainId>7290027600007</ChainId>
  <StoreId>001</StoreId>
  <Items Count="3">
    <Item>
      <ItemCode>7290000000999</ItemCode>
      <ItemName>מוצר בדיקה</ItemName>
      <!-- Missing ItemPrice -->
    </Item>
    <Item>
      <!-- Missing ItemCode -->
      <ItemName>מוצר ללא ברקוד</ItemName>
      <ItemPrice>10.00</ItemPrice>
    </Item>
    <Item>
      <ItemCode>7290000001000</ItemCode>
      <!-- Missing ItemName -->
      <ItemPrice>15.00</ItemPrice>
    </Item>
  </Items>
</root>"""

# Utility functions for tests
def get_sample_xml(chain: str, xml_type: str) -> str:
    """Get sample XML for a specific chain and type"""
    samples = {
        'shufersal': {
            'stores': SHUFERSAL_STORES_XML,
            'prices': SHUFERSAL_PRICES_XML
        },
        'victory': {
            'stores': VICTORY_STORES_XML,
            'prices': VICTORY_PRICES_XML,
        }
    }
    return samples.get(chain, {}).get(xml_type, "")


def get_gzipped_xml(xml_content: str) -> bytes:
    """Convert XML string to gzipped bytes (as returned by real servers)"""
    import gzip
    return gzip.compress(xml_content.encode('utf-8'))


# Sample parsed data for validation
EXPECTED_SHUFERSAL_STORE = {
    'store_id': '1',  # Leading zeros removed
    'name': 'שלי ת"א- בן יהודה',
    'address': 'בן יהודה 79',
    'city': 'תל אביב'
}

EXPECTED_VICTORY_STORE = {
    'store_id': '016',  # No leading zeros to remove
    'name': 'פלורנטין',
    'address': 'סלמה 53',
    'city': 'תל אביב'
}

EXPECTED_SHUFERSAL_PRICE = {
    'store_id': '1',  # Leading zeros removed
    'barcode': '7290000000001',
    'name': 'חלב טרה 3% בקרטון 1 ליטר',
    'price': 5.90
}

EXPECTED_VICTORY_PRICE = {
    'store_id': '74',  # Leading zeros removed
    'barcode': '7290000000001',
    'name': 'חלב טרה 3% 1 ליטר',
    'price': 6.20
}
