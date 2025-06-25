# tests/fixtures/sample_products.py

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from database.new_models import Chain, Branch, Product, ChainProduct, BranchPrice
from datetime import datetime

# Sample cart items for testing
SAMPLE_CART_ITEMS = [
    {"barcode": "7290000000001", "quantity": 2, "name": "חלב טרה 3%"},
    {"barcode": "7290000000002", "quantity": 1, "name": "לחם אחיד"},
    {"barcode": "7290000000003", "quantity": 3, "name": "ביצים L"},
    {"barcode": "7290000000004", "quantity": 1, "name": "גבינה צהובה"},
    {"barcode": "7290000000005", "quantity": 2, "name": "עגבניות"}
]


def create_test_database_data(db_session: Session) -> Dict[str, Any]:
    """Create comprehensive test data for database"""

    # Clear existing data
    db_session.query(BranchPrice).delete()
    db_session.query(ChainProduct).delete()
    db_session.query(Product).delete()
    db_session.query(Branch).delete()
    db_session.query(Chain).delete()
    db_session.commit()

    # Create chains
    chains = {}
    chain_data = [
        ('shufersal', 'שופרסל'),
        ('victory', 'ויקטורי'),
        ('yochananof', 'יוחננוף'),
        ('rami_levy', 'רמי לוי')
    ]

    for name, display_name in chain_data:
        chain = Chain(name=name, display_name=display_name)
        db_session.add(chain)
        chains[name] = chain

    db_session.commit()

    # Create branches
    branches = {}
    branch_data = [
        # Shufersal branches
        ('shufersal_dizengoff', chains['shufersal'].chain_id, '001', 'שופרסל דיזנגוף', 'תל אביב', 'דיזנגוף 50'),
        ('shufersal_ramat_gan', chains['shufersal'].chain_id, '002', 'שופרסל רמת גן', 'רמת גן', 'ביאליק 136'),
        ('shufersal_haifa', chains['shufersal'].chain_id, '003', 'שופרסל חיפה', 'חיפה', 'הרצל 15'),

        # Victory branches
        ('victory_tlv', chains['victory'].chain_id, '101', 'ויקטורי תל אביב', 'תל אביב', 'אלנבי 100'),
        ('victory_ramat_gan', chains['victory'].chain_id, '102', 'ויקטורי רמת גן', 'רמת גן', 'ז\'בוטינסקי 55'),
        ('victory_haifa', chains['victory'].chain_id, '103', 'ויקטורי חיפה', 'חיפה', 'בן גוריון 50'),

        # Yochananof branches
        ('yochananof_tlv', chains['yochananof'].chain_id, '201', 'יוחננוף תל אביב', 'תל אביב', 'נמיר 200'),
        ('yochananof_ramat_gan', chains['yochananof'].chain_id, '202', 'יוחננוף רמת גן', 'רמת גן', 'אבא הלל 100'),

        # Rami Levy branches
        ('rami_levy_tlv', chains['rami_levy'].chain_id, '301', 'רמי לוי תל אביב', 'תל אביב', 'לה גוארדיה 50'),
        ('rami_levy_ramat_gan', chains['rami_levy'].chain_id, '302', 'רמי לוי רמת גן', 'רמת גן', 'המעגל 10')
    ]

    for key, chain_id, branch_id, name, city, address in branch_data:
        branch = Branch(
            chain_id=chain_id,
            branch_id=branch_id,
            name=name,
            city=city,
            address=address
        )
        db_session.add(branch)
        branches[key] = branch

    db_session.commit()

    # Create products
    products = {}
    product_data = [
        ('7290000000001', 'חלב טרה 3%', 'טרה'),
        ('7290000000002', 'לחם אחיד', 'ברמן'),
        ('7290000000003', 'ביצים L', 'תנובה'),
        ('7290000000004', 'גבינה צהובה', 'תנובה'),
        ('7290000000005', 'עגבניות', 'שדות'),
        ('7290000000006', 'מלפפונים', 'שדות'),
        ('7290000000007', 'במבה', 'אסם'),
        ('7290000000008', 'ביסלי', 'אסם'),
        ('7290000000009', 'קולה 1.5 ליטר', 'קוקה קולה'),
        ('7290000000010', 'מים מינרלים', 'נביעות')
    ]

    # Create base products
    base_products = {}
    for barcode, name, manufacturer in product_data:
        product = Product(
            barcode=barcode,
            name=name,
            manufacturer=manufacturer
        )
        db_session.add(product)
        base_products[barcode] = product

    db_session.commit()

    # Create chain products (products per chain)
    for chain_name, chain in chains.items():
        for barcode, name, manufacturer in product_data:
            # Vary product names slightly per chain
            if chain_name == 'victory' and 'טרה' in name:
                name = name.replace('טרה', 'תנובה')
            elif chain_name == 'rami_levy' and 'תנובה' in name:
                name = name.replace('תנובה', 'שטראוס')

            key = f"{chain_name}_{barcode}"
            chain_product = ChainProduct(
                chain_id=chain.chain_id,
                barcode=barcode,
                name=name
            )
            db_session.add(chain_product)
            products[key] = chain_product

    db_session.commit()

    # Create prices
    prices = {}

    # Price variations by chain (multipliers)
    chain_price_multipliers = {
        'shufersal': 1.0,
        'victory': 0.95,
        'yochananof': 1.05,
        'rami_levy': 0.90
    }

    # Base prices
    base_prices = {
        '7290000000001': 5.90,  # חלב
        '7290000000002': 7.50,  # לחם
        '7290000000003': 14.90, # ביצים
        '7290000000004': 22.90, # גבינה
        '7290000000005': 3.90,  # עגבניות
        '7290000000006': 4.90,  # מלפפונים
        '7290000000007': 6.90,  # במבה
        '7290000000008': 7.90,  # ביסלי
        '7290000000009': 8.90,  # קולה
        '7290000000010': 3.50   # מים
    }

    # Create prices for each product in each branch
    for branch_key, branch in branches.items():
        chain_name = branch_key.split('_')[0]

        # Not all products available in all branches
        available_products = list(product_data)
        if 'haifa' in branch_key:
            # Haifa branches have fewer products
            available_products = available_products[:7]

        for barcode, _, _ in available_products:
            product_key = f"{chain_name}_{barcode}"
            if product_key in products:
                base_price = base_prices[barcode]
                multiplier = chain_price_multipliers[chain_name]

                # Add some city-based variation
                if 'tlv' in branch_key:
                    multiplier *= 1.05  # Tel Aviv is more expensive
                elif 'haifa' in branch_key:
                    multiplier *= 0.98  # Haifa is slightly cheaper

                price_value = round(base_price * multiplier, 2)

                price_key = f"{branch_key}_{barcode}"
                price = BranchPrice(
                    chain_product_id=products[product_key].chain_product_id,
                    branch_id=branch.branch_id,
                    price=price_value,
                    last_updated=datetime.utcnow()
                )
                db_session.add(price)
                prices[price_key] = price

    db_session.commit()

    return {
        "chains": chains,
        "branches": branches,
        "products": products,
        "prices": prices,
        "base_products": base_products
    }
