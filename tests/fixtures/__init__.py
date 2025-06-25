"""
Test fixtures and sample data.

This package contains reusable test data and mock responses.
"""

# Import sample products but handle if file doesn't exist
try:
    from .sample_products import *
except ImportError:
    pass

# Import sample XMLs but handle if file doesn't exist
try:
    from .sample_xmls import *
except ImportError:
    pass
