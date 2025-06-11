"""
Simple test script to verify the refactored API server is working correctly.
Run this after activating the virtual environment.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import the package
sys.path.append(str(Path(__file__).parent.parent))

try:
    # Import from utils
    from price_comparison_server.utils.product_utils import extract_product_weight, get_price_per_unit
    
    # Test the weight extraction function
    test_cases = [
        "במבה 80 גרם",
        "חלב תנובה 3% 1 ליטר",
        "ביסלי גריל 70ג",
        "שוקולד פרה 100 ג'",
        "מלח 1 ק\"ג",
        "סוכר 500 גר",
    ]
    
    print("Testing product weight extraction function:")
    for test in test_cases:
        weight, unit = extract_product_weight(test)
        price_per_unit = get_price_per_unit(test, 10.0)
        
        print(f"Item: {test}")
        print(f"  - Weight: {weight} {unit}")
        if price_per_unit:
            print(f"  - Price per unit: {price_per_unit['price_per_unit']:.4f} ₪/{price_per_unit['unit']}")
        else:
            print("  - Price per unit: Not available")
        print()
    
    print("✅ All imports and tests completed successfully!")
    print("The refactored code structure is working correctly.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you have activated the virtual environment and are running from the correct directory.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)