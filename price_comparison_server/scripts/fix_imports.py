#!/usr/bin/env python3
# price_comparison_server/scripts/fix_imports.py

import os
from pathlib import Path

print("Fixing import issues...")

# Fix services/__init__.py
services_init = Path(__file__).parent.parent / 'services' / '__init__.py'
with open(services_init, 'w') as f:
    f.write('''"""
Service modules for the price comparison server.
"""

# Import only the new services that work
# We'll add more as we implement them
''')

print("✓ Fixed services/__init__.py")

# Fix utils/__init__.py
utils_init = Path(__file__).parent.parent / 'utils' / '__init__.py'
with open(utils_init, 'w') as f:
    f.write('''"""
Utility modules for the price comparison server.
"""

# We'll add imports as we implement the utilities
''')

print("✓ Fixed utils/__init__.py")

print("\nNow testing imports...")

try:
    # Import from the fixed services
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from services.cart_service import CartComparisonService, CartItem
    print("✓ Successfully imported CartComparisonService")
    
    from database.connection import get_db
    from database.new_models import Chain, Branch, ChainProduct, BranchPrice
    print("✓ Successfully imported database models")
    
    print("\n✅ All imports fixed! You can now run the full cart comparison test.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("You may need to manually fix the imports.")
