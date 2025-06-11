# Champion Cart Server Documentation

This document provides a comprehensive explanation of the Champion Cart price comparison server. It details each component of the codebase, explaining how different modules work together to provide price comparison and shopping cart optimization.

## Table of Contents

1. [Overview](#overview)
2. [Main Server (api_server.py)](#main-server-api_serverpy)
3. [Server Runner (run_server.py)](#server-runner-run_serverpy)
4. [Data Models](#data-models)
5. [Database Utilities](#database-utilities)
6. [Authentication Routes](#authentication-routes)
7. [Cart Routes](#cart-routes)
8. [Price Routes](#price-routes)
9. [Search Service](#search-service)
10. [Product Utilities](#product-utilities)
11. [Data Scraping](#data-scraping)
12. [Summary](#summary)

## Overview

Champion Cart is a price comparison application that helps users find the best prices for groceries across multiple supermarket chains in Israel. The server component provides:

- APIs for searching products and comparing prices
- Shopping cart price optimization
- User authentication and saved carts
- Automated price data collection

The application is built using FastAPI, SQLite, and Python, with a modular architecture that separates concerns into different components.

## Main Server (api_server.py)

This is the main entry point for the FastAPI application. It sets up the server, registers routes, and initializes background tasks.

```python
from fastapi import FastAPI
import threading
import schedule
import time
import sys
import os

# Add the project root to sys.path for proper imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import from server module for scheduled scraping
from server import scrape_shufersal, scrape_victory

# Import database initializations
from utils.db_utils import init_user_db, init_cart_db
from routes.auth_routes import router as auth_router
from routes.price_routes import router as price_router
from routes.cart_routes import router as cart_router

# Initialize databases
init_user_db()
init_cart_db()

# Create the FastAPI application
app = FastAPI(
    title="Champion Cart API", 
    description="API for the Champion Cart price comparison application with improved search and price calculation. <br/> Currently supports Victory & Shufersal!", 
    version="1.1"
)

# Include routers
app.include_router(auth_router)
app.include_router(price_router)
app.include_router(cart_router)

@app.get("/")
def home():
    return {
        "message": "Welcome to the Champion Cart API",
        "version": "1.1",
        "improvements": [
            "Enhanced price comparison with better product matching",
            "Improved search functionality across store chains",
            "More accurate cheapest cart calculation"
        ]
    }

# Run scheduled scraping on startup
def run_scheduled_tasks():
    # scrape_shufersal()
    # scrape_victory()
    schedule.every(1).hour.do(scrape_shufersal)
    schedule.every(1).hour.do(scrape_victory)

    while True:
        schedule.run_pending()
        time.sleep(1)

# Start scheduled scraping in a separate thread
def start_scheduled_scraping():
    threading.Thread(target=run_scheduled_tasks, daemon=True).start()

# Call start_scheduled_scraping when the app starts
@app.on_event("startup")
def startup_event():
    start_scheduled_scraping()
```

### Key Components:

1. **Imports and Path Configuration**:
   - Sets up Python imports and adds the project root to the import path

2. **Database Initialization**:
   - Creates user and cart database tables if they don't exist

3. **FastAPI App Creation**:
   - Creates the main FastAPI application with metadata

4. **Router Registration**:
   - Includes routers for authentication, price endpoints, and cart functionality

5. **Root Endpoint**:
   - Defines a simple home page endpoint that returns basic API information

6. **Scheduled Task Setup**:
   - Sets up hourly scraping of supermarket data using a background thread
   - Uses schedule.every(1).hour.do() to register hourly tasks

7. **App Startup Event**:
   - Registers the scraping thread to start when the API server starts up

## Server Runner (run_server.py)

This is a convenience script to run the FastAPI application:

```python
#!/usr/bin/env python
"""
Simple wrapper script to run the API server.
This automatically handles imports and module paths.
"""
import sys
import os
import uvicorn

def main():
    """Run the API server."""
    print("Starting Price Comparison API Server...")
    print("Press Ctrl+C to stop the server.")
    
    # Get command line arguments
    host = "0.0.0.0"  # Listen on all network interfaces
    port = 8000
    reload = True
    
    # Extract port number if provided
    for arg in sys.argv:
        if arg.startswith("--port="):
            try:
                port = int(arg.split("=")[1])
            except (IndexError, ValueError):
                print(f"Invalid port format: {arg}. Using default port 8000.")
    
    # Run the improved server file
    app = "api_server:app"
    
    # Run the server
    print(f"Server running at http://{host}:{port}")
    print(f"Documentation available at http://localhost:{port}/docs")
    uvicorn.run(app, host=host, port=port, reload=reload)

if __name__ == "__main__":
    main()
```

### Key Components:

1. **Main Function**:
   - Sets default server configuration (host 0.0.0.0, port 8000)
   - Processes command-line arguments to allow custom port
   - Specifies the application entry point as "api_server:app"
   - Starts the uvicorn server with hot-reloading enabled for development

2. **Script Execution Check**:
   - Standard Python pattern to execute main() only when run directly

## Data Models

The application uses Pydantic models to define data structures and validate input/output.

### models/data_models.py

```python
from pydantic import BaseModel
from typing import List, Optional

class Price(BaseModel):
    snif_key: str
    item_code: str
    item_name: str
    item_price: float
    timestamp: str

class CartItem(BaseModel):
    item_name: str
    quantity: int

class CartRequest(BaseModel):
    city: str
    items: List[CartItem]

class SaveCartRequest(BaseModel):
    cart_name: str
    email: str
    city: str
    items: List[CartItem]
```

### Key Models:

1. **Price**:
   - Represents a single product price from a store database
   - Includes store ID, product code, name, price, and timestamp

2. **CartItem**:
   - Represents a single item in a shopping cart
   - Includes product name and quantity

3. **CartRequest**:
   - Used for price comparison between stores
   - Specifies city and list of items to compare

4. **SaveCartRequest**:
   - Used when saving a shopping cart for a user
   - Includes cart name, user email, city, and items

### models/user_models.py

```python
from pydantic import BaseModel

class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str
```

### Key Models:

1. **UserRegister**:
   - Used when registering a new user
   - Includes email and password

2. **UserLogin**:
   - Used for user authentication
   - Includes email and password for verification

## Database Utilities

The utils/db_utils.py file contains database utilities for connecting to and initializing databases:

```python
import sqlite3
import os
from fastapi import HTTPException

# Constants
USER_DB = "users.db"
DBS = {
    "shufersal": "shufersal_prices",
    "victory": "victory_prices"
}

def get_corrected_city_path(chain_dir, city_name):
    """Find the correct case for city directories that may have case differences."""
    if not os.path.exists(chain_dir):
        return None
        
    for dir_name in os.listdir(chain_dir):
        if dir_name.lower() == city_name.lower():
            return os.path.join(chain_dir, dir_name)
    return None

def init_user_db():
    """Ensure user database exists with appropriate tables."""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def init_cart_db():
    """Ensure cart database exists with appropriate tables."""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS carts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cart_name TEXT NOT NULL,
            email TEXT NOT NULL,
            items TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_db_connection(db_name: str, city: str, snif_key: str):
    """Get a database connection for a specific store."""
    db_path = os.path.join(DBS[db_name], city, f"{snif_key}.db")
    
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail=f"Database for snif_key '{snif_key}' in {city} not found.")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
```

### Key Functions:

1. **get_corrected_city_path**:
   - Handles case sensitivity issues with city names in directories
   - Essential for cross-platform compatibility

2. **init_user_db**:
   - Initializes the user database with appropriate schema
   - Creates a 'users' table if it doesn't exist

3. **init_cart_db**:
   - Initializes the cart database table
   - Creates a 'carts' table if it doesn't exist

4. **get_db_connection**:
   - Creates and returns a database connection for a specific store
   - Verifies the database exists and configures row_factory

## Authentication Routes

The routes/auth_routes.py file defines authentication endpoints:

```python
from fastapi import APIRouter, HTTPException
import sqlite3
import sys
import os

# Add project root to path for imports if needed
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import directly since we've ensured the path is correct
from models.user_models import UserRegister, UserLogin
from utils.auth_utils import hash_password, verify_password, create_access_token
from utils.db_utils import USER_DB

router = APIRouter(tags=["authentication"])

@router.post("/register")
def register_user(user: UserRegister):
    try:
        conn = sqlite3.connect(USER_DB)
        cursor = conn.cursor()
        
        # Check if the email is already registered
        cursor.execute("SELECT email FROM users WHERE email = ?", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash the password
        hashed_password = hash_password(user.password)
        
        # Insert user into the database
        cursor.execute("""
            INSERT INTO users (email, password) VALUES (?, ?)
        """, (user.email, hashed_password))
        
        conn.commit()
        conn.close()
        
        return {"message": "User registered successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.post("/login")
def login_user(user: UserLogin):
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    cursor.execute("SELECT password FROM users WHERE email = ?", (user.email,))
    record = cursor.fetchone()
    
    conn.close()
    
    if not record or not verify_password(user.password, record[0]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer"}
```

### Key Endpoints:

1. **/register**:
   - Registers a new user with email and password
   - Checks if email already exists
   - Hashes the password for secure storage

2. **/login**:
   - Validates login credentials
   - Returns a JWT token for authenticated requests

## Cart Routes

The routes/cart_routes.py file manages shopping cart functionality:

```python
from fastapi import APIRouter, HTTPException
import sqlite3
from typing import List
import sys
import os

# Add project root to path for imports if needed
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.data_models import SaveCartRequest
from utils.db_utils import USER_DB
from services.search_service import search_products_by_name_and_city

router = APIRouter(tags=["carts"])

@router.post("/save-cart")
def save_cart(request: SaveCartRequest):
    try:
        conn = sqlite3.connect(USER_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT email FROM users WHERE email = ?", (request.email,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if cart already exists
        cursor.execute("""
            SELECT cart_name FROM carts 
            WHERE email = ? AND cart_name = ?
        """, (request.email, request.cart_name))
        
        if cursor.fetchone():
            # If cart exists, delete it and its items
            cursor.execute("""
                DELETE FROM cart_items WHERE cart_id IN 
                (SELECT id FROM carts WHERE email = ? AND cart_name = ?)
            """, (request.email, request.cart_name))
            
            cursor.execute("""
                DELETE FROM carts WHERE email = ? AND cart_name = ?
            """, (request.email, request.cart_name))
        
        # Create new cart
        cursor.execute("""
            INSERT INTO carts (email, cart_name, city) VALUES (?, ?, ?)
        """, (request.email, request.cart_name, request.city))
        
        cart_id = cursor.lastrowid
        
        # Insert cart items
        for item in request.items:
            cursor.execute("""
                INSERT INTO cart_items (cart_id, item_name, quantity) VALUES (?, ?, ?)
            """, (cart_id, item.item_name, item.quantity))
        
        conn.commit()
        conn.close()
        
        return {"message": "Cart saved successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/savedcarts/{email}")
def get_saved_carts(email: str, city: str = None):
    try:
        conn = sqlite3.connect(USER_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user's saved carts
        if city:
            cursor.execute("""
                SELECT id, cart_name FROM carts WHERE email = ? AND city = ?
            """, (email, city))
        else:
            cursor.execute("""
                SELECT id, cart_name FROM carts WHERE email = ?
            """, (email,))
        
        carts = []
        for cart_row in cursor.fetchall():
            cart_id = cart_row["id"]
            cart_name = cart_row["cart_name"]
            
            # Get items for this cart
            cursor.execute("""
                SELECT item_name, quantity FROM cart_items WHERE cart_id = ?
            """, (cart_id,))
            
            items = []
            for item_row in cursor.fetchall():
                item = dict(item_row)
                
                # Try to get current price for this item
                if city:
                    try:
                        search_results = search_products_by_name_and_city(city, item["item_name"])
                        if search_results and len(search_results) > 0:
                            item["price"] = search_results[0]["price"]
                        else:
                            item["price"] = None
                    except:
                        item["price"] = None
                else:
                    item["price"] = None
                
                items.append(item)
            
            carts.append({"cart_name": cart_name, "items": items})
        
        return {"email": email, "saved_carts": carts}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
```

### Key Endpoints:

1. **/save-cart**:
   - Saves a shopping cart for a user
   - Replaces existing cart with the same name
   - Stores cart items with quantities

2. **/savedcarts/{email}**:
   - Retrieves a user's saved carts
   - Optionally fetches current prices based on city
   - Returns cart data with items and prices

## Price Routes

The routes/price_routes.py file contains the main price-related endpoints:

```python
from fastapi import APIRouter, HTTPException
import sqlite3
import os
import sys
from typing import List, Dict, Any, Set
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path if needed
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import models and utilities
from models.data_models import Price, CartRequest, CartItem
from utils.db_utils import get_db_connection, DBS, get_corrected_city_path

# Import search function for advanced product matching
from services.search_service import search_products_by_name_and_city

router = APIRouter(tags=["prices"])
```

### Key Endpoints:

1. **/prices/{db_name}/store/{snif_key}**:
   - Returns all prices from a specific store
   - Useful for browsing a store's complete inventory

2. **/prices/{db_name}/item_code/{item_code}**:
   - Searches for a product by barcode across all stores
   - Shows how prices vary for the exact same product

3. **/prices/{db_name}/item_name/{item_name}**:
   - Fuzzy search on product names
   - Returns similar products across all stores in a chain

4. **/cities-list-with-stores**:
   - Lists cities with store counts for each chain
   - Useful for UI dropdowns showing available locations

5. **/cities-list**:
   - Simple list of available cities
   - Used for basic selection interfaces

6. **/cheapest-cart-all-chains**:
   - The core feature - compares shopping cart prices across stores
   - Uses advanced product matching to find the best deals
   - Returns detailed price comparison with savings information

7. **/prices/by-item/{city}/{item_name}**:
   - Searches for a product in a specific city across all chains
   - Returns balanced results for fair comparison

## Search Service

The services/search_service.py file contains the core search functionality:

### Key Functions:

1. **search_products_by_name_and_city**:
   - Main search function for finding products by name
   - Handles Hebrew text with special patterns
   - Returns balanced results across chains

2. **balance_results**:
   - Ensures results are evenly distributed between chains
   - Prevents results from one chain dominating the list

3. **group_products_by_item_code**:
   - Groups identical products by barcode across chains
   - Essential for accurate price comparison

## Product Utilities

The utils/product_utils.py file contains utilities for product data manipulation:

```python
import re
from typing import Tuple, Dict, Optional, Any, List

def extract_product_weight(item_name: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Extracts weight or volume information from product names.
    Returns a tuple of (value, unit) or (None, None) if not found.
    """
    # Common units in Hebrew product descriptions
    units = {
        'גרם': 'g',
        'ג': 'g',
        'גר': 'g',
        "ג'": 'g',
        'קג': 'kg', 
        'ק"ג': 'kg',
        'קילו': 'kg',
        'ליטר': 'l',
        'ל': 'l',
        'מל': 'ml',
        'מ"ל': 'ml',
        'יחידות': 'unit'
    }
    
    # Pattern to match number + unit
    pattern = r'(\d+(?:\.\d+)?)\s*(' + '|'.join(units.keys()) + r')'
    matches = re.findall(pattern, item_name)
    
    if matches:
        value, unit = matches[0]
        return (float(value), units[unit])
    
    # Try to match common formats like "80g" without space
    compact_pattern = r'(\d+(?:\.\d+)?)(' + '|'.join(['ג', 'גר', 'קג', 'ל', 'מל']) + r')'
    matches = re.findall(compact_pattern, item_name)
    
    if matches:
        value, unit = matches[0]
        return (float(value), units[unit])
        
    return (None, None)

def get_price_per_unit(item_name: str, price: float) -> Optional[Dict[str, Any]]:
    """
    Calculate the price per unit (gram, ml, etc) to enable comparison
    between different package sizes.
    """
    value, unit = extract_product_weight(item_name)
    
    if value is None or value == 0:
        return None
        
    # Convert to base unit (g, ml)
    if unit == 'kg':
        value = value * 1000
        unit = 'g'
    elif unit == 'l':
        value = value * 1000
        unit = 'ml'
        
    return {
        'price_per_unit': price / value,
        'unit': unit,
        'value': value
    }

def generate_cross_chain_comparison(product):
    """Generate detailed cross-chain price comparison for identical products"""
    if 'prices' not in product or len(product['prices']) < 2:
        return {}
    
    # Get unique chains and their lowest prices
    chain_prices = {}
    for price in product['prices']:
        chain = price.get('chain')
        if not chain:
            continue
        
        if chain not in chain_prices or price['price'] < chain_prices[chain]['price']:
            chain_prices[chain] = {
                'price': price['price'],
                'store_id': price['store_id']
            }
    
    # Must have at least two chains for comparison
    if len(chain_prices) < 2:
        return {}
    
    # Find best and worst deals
    chains = list(chain_prices.keys())
    lowest_chain = min(chains, key=lambda c: chain_prices[c]['price'])
    highest_chain = max(chains, key=lambda c: chain_prices[c]['price'])
    
    lowest_price = chain_prices[lowest_chain]['price']
    highest_price = chain_prices[highest_chain]['price']
    
    # Calculate savings
    savings = highest_price - lowest_price
    savings_percent = (savings / highest_price) * 100 if highest_price > 0 else 0
    
    return {
        'best_deal': {
            'chain': lowest_chain,
            'price': lowest_price,
            'store_id': chain_prices[lowest_chain]['store_id']
        },
        'worst_deal': {
            'chain': highest_chain,
            'price': highest_price,
            'store_id': chain_prices[highest_chain]['store_id']
        },
        'savings': savings,
        'savings_percent': savings_percent,
        'identical_product': True
    }
```

### Key Functions:

1. **extract_product_weight**:
   - Parses Hebrew product names to extract weight/volume information
   - Uses regular expressions to handle different unit formats
   - Returns standardized values for comparison

2. **get_price_per_unit**:
   - Calculates unit price (price per gram, per ml, etc.)
   - Normalizes units for fair comparison
   - Essential for comparing products of different sizes

3. **generate_cross_chain_comparison**:
   - Creates price comparisons for identical products across chains
   - Calculates potential savings by buying from the cheapest store
   - Used for shopping cart optimization

## Data Scraping

The server.py file contains functionality for scraping price data from supermarket websites:

### Key Functions:

1. **get_store_city**:
   - Maps store IDs to city names
   - Crucial for organizing data geographically

2. **create_database_for_snif_key**:
   - Creates SQLite databases for storing price data
   - Organizes by chain and city

3. **save_to_database_by_snif_key**:
   - Stores scraped price data in the appropriate database
   - Manages data replacement to keep information current

4. **download_and_extract_gz**:
   - Downloads compressed price data files
   - Extracts the data for processing

5. **parse_shufersal_xml / parse_victory_xml**:
   - Parses price data from each chain's XML format
   - Extracts product details and prices

6. **scrape_shufersal / scrape_victory**:
   - Main functions that orchestrate the scraping process
   - Download, parse, and store price data from each chain

## Summary

The Champion Cart server is a well-designed FastAPI application that provides price comparison functionality across Israeli supermarket chains:

1. **Modular Architecture**:
   - Clear separation of concerns into different modules
   - Routes organized by functionality (auth, cart, prices)
   - Utilities separate from business logic

2. **Data Flow**:
   - Price data is scraped from supermarket websites
   - Stored in SQLite databases organized by chain and city
   - Accessed through API endpoints for comparison
   - Shopping carts can be optimized for the best total price

3. **Key Features**:
   - Product search with balanced results across chains
   - Shopping cart price optimization
   - User authentication and saved carts
   - Price per unit calculation for fair comparison
   - Cross-chain product matching by barcode

4. **Performance Considerations**:
   - Data scraping runs in a background thread
   - Price data is stored locally for fast access
   - Search results are balanced between chains
   - Complex queries use optimized SQLite features

This documentation provides a comprehensive overview of how the Champion Cart server works, explaining each component and how they interact to deliver price comparison functionality.