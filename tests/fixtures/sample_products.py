"""
Sample product data for tests.

This module provides test data for products, carts, and prices.
"""

from typing import List, Dict, Any
from datetime import datetime


# Sample cart items for testing
SAMPLE_CART_ITEMS = [
    {
        "barcode": "7290000000001",
        "quantity": 2,
        "name": "חלב טרה 3%"
    },
    {
        "barcode": "7290000000002",
        "quantity": 1,
        "name": "לחם אחיד פרוס"
    },
    {
        "barcode": "7290000000003",
        "quantity": 1,
        "name": "ביצים L"
    }
]


def create_test_database_data(db_session):
    """Create comprehensive test data in the database"""
    from database.new_models import Chain, Branch, Product, ChainProduct, BranchPrice

    # Create chains
    shufersal = Chain(name='shufersal', display_name='שופרסל')
    victory = Chain(name='victory', display_name='ויקטורי')

    db_session.add_all([shufersal, victory])
    db_session.commit()

    # Create branches
    branches = [
        # Shufersal branches
        Branch(
            chain_id=shufersal.chain_id,
            store_id='001',
            name='שופרסל דיזנגוף',
            address='דיזנגוף 50',
            city='תל אביב'
        ),
        Branch(
            chain_id=shufersal.chain_id,
            store_id='002',
            name='שופרסל רמת אביב',
            address='איינשטיין 40',
            city='תל אביב'
        ),
        Branch(
            chain_id=shufersal.chain_id,
            store_id='010',
            name='שופרסל חיפה',
            address='חורב 15',
            city='חיפה'
        ),
        # Victory branches
        Branch(
            chain_id=victory.chain_id,
            store_id='001',
            name='ויקטורי דיזנגוף סנטר',
            address='דיזנגוף סנטר',
            city='תל אביב'
        ),
        Branch(
            chain_id=victory.chain_id,
            store_id='002',
            name='ויקטורי רמת החייל',
            address='הברזל 15',
            city='תל אביב'
        ),
        Branch(
            chain_id=victory.chain_id,
            store_id='005',
            name='ויקטורי גרנד קניון',
            address='גרנד קניון',
            city='חיפה'
        )
    ]

    db_session.add_all(branches)
    db_session.commit()

    # Create products for each chain
    products_data = [
        # Common products available in both chains
        ('7290000000001', 'חלב טרה 3%', 'dairy'),
        ('7290000000002', 'לחם אחיד פרוס', 'bakery'),
        ('7290000000003', 'ביצים L 12 יח', 'dairy'),
        ('7290000000004', 'עגבניות', 'produce'),
        ('7290000000005', 'מים מינרלים 1.5 ליטר', 'beverages'),
        # Additional products
        ('7290000000010', 'גבינה צהובה 200 גרם', 'dairy'),
        ('7290000000011', 'קוטג 5%', 'dairy'),
        ('7290000000012', 'יוגורט דנונה', 'dairy'),
        ('7290000000013', 'קורנפלקס', 'cereals'),
        ('7290000000014', 'אורז בסמטי', 'grains'),
        ('7290000000015', 'פסטה ברילה', 'grains'),
        ('7290000000016', 'שמן זית', 'oils'),
        ('7290000000017', 'סוכר לבן', 'baking'),
        ('7290000000018', 'קמח', 'baking'),
        ('7290000000019', 'ביצים M 12 יח', 'dairy'),
        ('7290000000020', 'חלב תנובה 3%', 'dairy'),
    ]

    # Create products for both chains
    chain_products = []
    for chain in [shufersal, victory]:
        for barcode, name, category in products_data:
            # Slightly modify names for different chains
            product_name = name
            if chain.name == 'victory' and 'טרה' in name:
                product_name = name.replace('טרה', 'תנובה')

            chain_product = ChainProduct(
                chain_id=chain.chain_id,
                barcode=barcode,
                name=product_name
            )
            chain_products.append(chain_product)

    db_session.add_all(chain_products)
    db_session.commit()

    # Create prices for products in branches
    prices = []

    # Price mapping: (branch_store_id, barcode, price)
    price_data = {
        'shufersal': {
            '001': [  # Dizengoff branch
                ('7290000000001', 5.90),   # Milk
                ('7290000000002', 7.50),   # Bread
                ('7290000000003', 14.90),  # Eggs
                ('7290000000004', 6.90),   # Tomatoes
                ('7290000000005', 2.50),   # Water
                ('7290000000010', 24.90),  # Yellow cheese
                ('7290000000011', 4.50),   # Cottage cheese
                ('7290000000012', 3.90),   # Yogurt
            ],
            '002': [  # Ramat Aviv branch - slightly different prices
                ('7290000000001', 6.20),
                ('7290000000002', 7.90),
                ('7290000000003', 15.50),
                ('7290000000004', 7.50),
                ('7290000000005', 2.90),
                ('7290000000010', 25.90),
                ('7290000000011', 4.90),
            ],
            '010': [  # Haifa branch
                ('7290000000001', 5.50),
                ('7290000000002', 6.90),
                ('7290000000003', 13.90),
                ('7290000000004', 5.90),
                ('7290000000005', 2.20),
            ]
        },
        'victory': {
            '001': [  # Dizengoff Center
                ('7290000000001', 5.50),   # Milk - cheaper
                ('7290000000002', 8.90),   # Bread - more expensive
                ('7290000000003', 13.90),  # Eggs - cheaper
                ('7290000000004', 5.90),   # Tomatoes - cheaper
                ('7290000000005', 2.20),   # Water
                ('7290000000010', 22.90),  # Yellow cheese
                ('7290000000011', 4.20),   # Cottage cheese
                ('7290000000012', 3.50),   # Yogurt
            ],
            '002': [  # Ramat HaHayal
                ('7290000000001', 5.70),
                ('7290000000002', 8.50),
                ('7290000000003', 14.50),
                ('7290000000004', 6.50),
                ('7290000000005', 2.40),
            ],
            '005': [  # Haifa Grand Canyon
                ('7290000000001', 5.20),
                ('7290000000002', 7.90),
                ('7290000000003', 12.90),
                ('7290000000004', 5.50),
                ('7290000000005', 2.00),
            ]
        }
    }

    # Create price entries
    for chain_name, chain_prices in price_data.items():
        chain = shufersal if chain_name == 'shufersal' else victory

        for store_id, product_prices in chain_prices.items():
            # Find branch
            branch = next(b for b in branches if b.chain_id == chain.chain_id and b.store_id == store_id)

            for barcode, price in product_prices:
                # Find chain product
                chain_product = next(
                    cp for cp in chain_products
                    if cp.chain_id == chain.chain_id and cp.barcode == barcode
                )

                price_entry = BranchPrice(
                    chain_product_id=chain_product.chain_product_id,
                    branch_id=branch.branch_id,
                    price=price,
                    last_updated=datetime.utcnow()
                )
                prices.append(price_entry)

    db_session.add_all(prices)
    db_session.commit()

    return {
        'chains': {'shufersal': shufersal, 'victory': victory},
        'branches': branches,
        'products': chain_products,
        'prices': prices
    }


# Sample test data for specific test scenarios
HEBREW_PRODUCT_NAMES = [
    "חלב טרה 3%",
    "לחם אחיד פרוס",
    "ביצים L",
    "עגבניות",
    "קוטג' 5%",
    "צ'יפס תפוצ'יפס",
    "במבה אסם",
    "שוקולד עלית"
]


HEBREW_CITIES = [
    "תל אביב",
    "ירושלים",
    "חיפה",
    "באר שבע",
    "רמת גן",
    "פתח תקווה",
    "ראשון לציון",
    "אשדוד"
]


SAMPLE_BARCODES = [
    "7290000000001",
    "7290000000002",
    "7290000000003",
    "7290000000004",
    "7290000000005",
    "7290000000010",
    "7290000000011",
    "7290000000012",
    "7290000000013",
    "7290000000014",
    "7290000000015",
    "7290000000016",
    "7290000000017",
    "7290000000018",
    "7290000000019",
    "7290000000020"
]


def get_sample_cart_for_city(city: str) -> Dict[str, Any]:
    """Get a sample cart appropriate for testing in a specific city"""
    return {
        "city": city,
        "items": SAMPLE_CART_ITEMS[:3]  # First 3 items
    }


def get_large_sample_cart() -> List[Dict[str, Any]]:
    """Get a large cart for performance testing"""
    return [
        {
            "barcode": barcode,
            "quantity": (i % 5) + 1,
            "name": f"Product {i}"
        }
        for i, barcode in enumerate(SAMPLE_BARCODES)
    ]
