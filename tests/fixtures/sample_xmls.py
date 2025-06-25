"""
Sample XML data for parser tests.

This module provides XML snippets for testing Shufersal and Victory parsers.
"""

import gzip
from io import BytesIO


# Shufersal store XML sample
SHUFERSAL_STORES_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<root>
    <Store>
        <StoreId>001</StoreId>
        <StoreName>שלי ת"א- בן יהודה</StoreName>
        <Address>בן יהודה 79</Address>
        <City>תל אביב</City>
        <ZipCode>12345</ZipCode>
    </Store>
    <Store>
        <StoreId>312</StoreId>
        <StoreName>דיל חיפה- קרית אליעזר</StoreName>
        <Address>ככר מאירהוף</Address>
        <City>חיפה</City>
        <ZipCode>54321</ZipCode>
    </Store>
</root>'''


# Shufersal prices XML sample
SHUFERSAL_PRICES_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<root>
    <Items>
        <Item>
            <ItemCode>7290000000001</ItemCode>
            <ItemName>חלב טרה 3%</ItemName>
            <ItemPrice>5.90</ItemPrice>
            <Quantity>1</Quantity>
            <UnitOfMeasure>יחידה</UnitOfMeasure>
        </Item>
        <Item>
            <ItemCode>7290000000002</ItemCode>
            <ItemName>לחם אחיד פרוס</ItemName>
            <ItemPrice>7.50</ItemPrice>
            <Quantity>1</Quantity>
            <UnitOfMeasure>יחידה</UnitOfMeasure>
        </Item>
        <Item>
            <ItemCode>7290000000003</ItemCode>
            <ItemName>ביצים L 12 יח'</ItemName>
            <ItemPrice>14.90</ItemPrice>
            <Quantity>12</Quantity>
            <UnitOfMeasure>מארז</UnitOfMeasure>
        </Item>
    </Items>
</root>'''


# Victory store XML sample
VICTORY_STORES_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<Branches>
    <Branch>
        <branch_code>001</branch_code>
        <branch_name>ויקטורי דיזנגוף סנטר</branch_name>
        <branch_address>דיזנגוף סנטר</branch_address>
        <city_name>תל אביב</city_name>
        <zip_code>12345</zip_code>
    </Branch>
    <Branch>
        <branch_code>005</branch_code>
        <branch_name>ויקטורי גרנד קניון</branch_name>
        <branch_address>גרנד קניון חיפה</branch_address>
        <city_name>חיפה</city_name>
        <zip_code>54321</zip_code>
    </Branch>
</Branches>'''


# Victory prices XML sample
VICTORY_PRICES_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<Products>
    <Product>
        <product_barcode>7290000000001</product_barcode>
        <product_name>חלב תנובה 3%</product_name>
        <unit_price>5.50</unit_price>
        <quantity>1</quantity>
        <unit_measure>יחידה</unit_measure>
    </Product>
    <Product>
        <product_barcode>7290000000002</product_barcode>
        <product_name>לחם אחיד פרוס</product_name>
        <unit_price>8.90</unit_price>
        <quantity>1</quantity>
        <unit_measure>יחידה</unit_measure>
    </Product>
</Products>'''


# Empty stores XML
EMPTY_STORES_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<root>
</root>'''


# Malformed XML
MALFORMED_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<root>
    <Store>
        <StoreId>001</StoreId>
        <StoreName>Test Store
        <!-- Missing closing tags -->
