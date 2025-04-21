from fastapi import FastAPI, HTTPException
import sqlite3
from pydantic import BaseModel
from typing import List, Optional
import os
import threading
import schedule
import time
import bcrypt
import jwt
import datetime

from server import scrape_shufersal, scrape_victory

app = FastAPI(title="Grocery Prices API", description="API to access grocery prices across supermarket chains. <br/> Currently supports Victory & Shufersal !", version="1.0")

SECRET_KEY = "iJJrwjxbCBE3OpbxKwexfmZLMCNlVkD1/LaA3o0Rx91e7dDkcd1ggiPctUjaYasY"  
ALGORITHM = "HS256"

USER_DB = "users.db"

DBS = {
    "shufersal": "shufersal_prices",
    "victory": "victory_prices"
}

# Ensure user database exists
def init_user_db():
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

init_user_db()

# Models
class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

def create_access_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# Endpoints
@app.post("/register")
def register(user: UserRegister):
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", 
                       (user.email, hash_password(user.password)))
        conn.commit()
        return {"message": "User registered successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="email already exists")
    finally:
        conn.close()

@app.post("/login")
def login(user: UserLogin):
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE email = ?", (user.email,))
    record = cursor.fetchone()
    conn.close()

    if not record or not verify_password(user.password, record[0]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer"}


def get_db_connection(db_name: str, city: str, snif_key: str):
    db_path = os.path.join(DBS[db_name], city, f"{snif_key}.db")
    
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail=f"Database for snif_key '{snif_key}' in {city} not found.")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

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

@app.get("/")
def home():
    return {"message": "Welcome to the Grocery Prices API"}

@app.get("/prices/{db_name}/store/{snif_key}", response_model=List[Price])
def get_prices_by_store(db_name: str, snif_key: str):
    if db_name not in DBS:
        raise HTTPException(status_code=400, detail="Invalid database name. Use 'shufersal' or 'victory'.")
    
    city = None
    for city_dir in os.listdir(DBS[db_name]):
        if os.path.exists(os.path.join(DBS[db_name], city_dir, f"{snif_key}.db")):
            city = city_dir
            break
    
    if not city:
        raise HTTPException(status_code=404, detail="Store not found")
    
    conn = get_db_connection(db_name, city, snif_key)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prices ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

@app.get("/prices/{db_name}/item_code/{item_code}", response_model=List[Price])
def get_prices_by_item_code(db_name: str, item_code: str):
    if db_name not in DBS:
        raise HTTPException(status_code=400, detail="Invalid database name. Use 'shufersal' or 'victory'.")
    
    prices = []
    for city in os.listdir(DBS[db_name]):
        city_path = os.path.join(DBS[db_name], city)
        if os.path.isdir(city_path):
            for db_file in os.listdir(city_path):
                if db_file.endswith(".db"):
                    snif_key = db_file.replace(".db", "")
                    conn = get_db_connection(db_name, city, snif_key)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM prices WHERE item_code = ?", (item_code,))
                    rows = cursor.fetchall()
                    conn.close()
                    prices.extend([dict(row) for row in rows])
    
    if not prices:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return prices

@app.get("/prices/{db_name}/item_name/{item_name}", response_model=List[Price])
def get_prices_by_item_name(db_name: str, item_name: str):
    if db_name not in DBS:
        raise HTTPException(status_code=400, detail="Invalid database name. Use 'shufersal' or 'victory'.")
    
    prices = []
    for city in os.listdir(DBS[db_name]):
        city_path = os.path.join(DBS[db_name], city)
        if os.path.isdir(city_path):
            for db_file in os.listdir(city_path):
                if db_file.endswith(".db"):
                    snif_key = db_file.replace(".db", "")
                    conn = get_db_connection(db_name, city, snif_key)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM prices WHERE item_name LIKE ?", ('%' + item_name + '%',))
                    rows = cursor.fetchall()
                    conn.close()
                    prices.extend([dict(row) for row in rows])
    
    return prices

@app.get("/cities-list-with-stores")
def get_cities_list_extended():
    cities_data = {}
    
    for db_name in DBS:
        db_path = DBS[db_name]
        for city in os.listdir(db_path):
            city_path = os.path.join(db_path, city)
            if os.path.isdir(city_path):
                if city not in cities_data:
                    cities_data[city] = {'shufersal': 0, 'victory': 0}
                
                store_count = len([f for f in os.listdir(city_path) if f.endswith('.db')])
                cities_data[city][db_name] = store_count
    
    formatted_cities = []
    for city, counts in cities_data.items():
        store_info = []
        if counts['shufersal'] > 0:
            store_info.append(f"{counts['shufersal']} shufersal")
        if counts['victory'] > 0:
            store_info.append(f"{counts['victory']} victory")
        formatted_cities.append(f"{city}: {', '.join(store_info)}")
    
    return formatted_cities

@app.get("/cities-list")
def get_cities_list():
    formatted_cities = []
    
    for db_name in DBS:
        db_path = DBS[db_name]
        for city in os.listdir(db_path):
            formatted_cities.append(f"{city}")
    return formatted_cities


@app.post("/cheapest-cart-all-chains")
def get_cheapest_cart_all_chains(cart_request: CartRequest):
    best_price = float('inf')
    best_store = None
    best_chain = None
    
    for db_name in DBS.keys():
        db_path = DBS[db_name]
        city_path = os.path.join(db_path, cart_request.city)
        
        if not os.path.exists(city_path):
            continue
            
        for db_file in os.listdir(city_path):
            if db_file.endswith(".db"):
                snif_key = db_file.replace(".db", "")
                total_price = 0
                items_found = True
                
                try:
                    conn = get_db_connection(db_name, cart_request.city, snif_key)
                    cursor = conn.cursor()
                    
                    for item in cart_request.items:
                        cursor.execute(""" 
                            SELECT item_price 
                            FROM prices 
                            WHERE item_name LIKE ? 
                            ORDER BY timestamp DESC 
                            LIMIT 1
                        """, ('%' + item.item_name + '%',))
                        result = cursor.fetchone()
                        
                        if result:
                            total_price += result['item_price'] * item.quantity
                        else:
                            items_found = False
                            break
                            
                    conn.close()
                    
                    if items_found and total_price < best_price:
                        best_price = total_price
                        best_store = snif_key
                        best_chain = db_name
                        
                except Exception as e:
                    continue
    
    if best_store is None:
        raise HTTPException(status_code=404, detail="Could not find all items in any single store")
    
    return {
        "chain": best_chain,
        "store_id": best_store,
        "total_price": best_price,
        "city": cart_request.city,
        "items": cart_request.items
    }

@app.get("/prices/by-item/{city}/{item_name}")
def get_prices_by_item_and_city(city: str, item_name: str):
    results = []
    
    # Log the search request
    print(f"Searching for '{item_name}' in city '{city}'")
    
    # Special case handling for specific searches
    specific_search_cases = {
        "במ": ["במבה", "ביסלי במבה", "חטיף במבה"],
        "ביס": ["ביסלי", "ביסלים"],
        "שוק": ["שוקולד", "שוקו"]
    }
    
    # Search through all supported chains
    for chain_name, db_name in DBS.items():
        city_path = os.path.join(db_name, city)
        
        # Skip if city doesn't exist in this chain
        if not os.path.exists(city_path):
            print(f"City '{city}' not found in chain '{chain_name}'")
            continue
            
        # Search through all store DBs in the city
        for store_db in os.listdir(city_path):
            if store_db.endswith('.db'):
                snif_key = store_db[:-3]  # Remove .db
                
                try:
                    conn = get_db_connection(chain_name, city, snif_key)
                    cursor = conn.cursor()
                    
                    # Add specific search terms for common Hebrew searches
                    search_patterns = []
                    
                    # Add special case patterns if this is a known search term
                    if item_name in specific_search_cases:
                        # Add exact common product searches for this term
                        for product in specific_search_cases[item_name]:
                            search_patterns.append(f'{product}%')  # Products starting with the common term
                        
                        print(f"Added special case patterns for '{item_name}'")
                    
                    # Then add the standard patterns
                    search_patterns.extend([
                        f'{item_name}%',                 # Starts with match (highest priority)
                        f' {item_name} ',                # Standalone word
                        f' {item_name}%',                # Word at beginning
                        f'%{item_name}%',                # Basic 'contains' match (lower priority)
                    ])
                    
                    # Add transliteration mappings for common Hebrew products
                    transliterations = {
                        'bamba': 'במבה',
                        'bisli': 'ביסלי',
                        'milk': 'חלב',
                        'water': 'מים',
                        'bread': 'לחם',
                        'eggs': 'ביצים',
                        'cheese': 'גבינה',
                        'rice': 'אורז',
                        'sugar': 'סוכר',
                        'salt': 'מלח',
                        'chicken': 'עוף',
                        'beef': 'בקר',
                        'fish': 'דג',
                        'vegetable': 'ירק',
                        'fruit': 'פרי',
                        'apple': 'תפוח',
                        'banana': 'בננה',
                        'orange': 'תפוז',
                        'tomato': 'עגבניה',
                        'cucumber': 'מלפפון',
                        'onion': 'בצל',
                        'potato': 'תפוח אדמה',
                        'carrot': 'גזר',
                        'chocolate': 'שוקולד'
                    }
                    
                    # Add Hebrew equivalents to search patterns if the search term is in English
                    if item_name.lower() in transliterations:
                        hebrew_term = transliterations[item_name.lower()]
                        search_patterns.extend([
                            f'{hebrew_term}%',             # Starts with Hebrew equivalent (high priority)
                            f'%{hebrew_term}%'            # Contains Hebrew equivalent
                        ])
                        print(f"Added Hebrew transliteration '{hebrew_term}' for '{item_name}'")
                    
                    # Try different search patterns
                    for pattern in search_patterns:
                        cursor.execute(""" 
                            SELECT snif_key, item_name, item_price, timestamp 
                            FROM prices 
                            WHERE item_name LIKE ? 
                            ORDER BY timestamp DESC
                            LIMIT 50
                        """, (pattern,))
                        
                        rows = cursor.fetchall()
                        
                        # If we found matches, add them and continue with other patterns to get more results
                        if rows:
                            for row in rows:
                                # Check if this item is already in results (avoid duplicates)
                                item_name = row['item_name']
                                if not any(r['item_name'] == item_name for r in results):
                                    results.append({
                                        "chain": chain_name,
                                        "store_id": snif_key,
                                        "item_name": item_name,
                                        "price": row['item_price'],
                                        "last_updated": row['timestamp']
                                    })
                    
                    conn.close()
                        
                except sqlite3.Error as e:
                    print(f"Database error when searching in {chain_name}/{city}/{snif_key}: {str(e)}")
                    continue
    
    if not results:
        print(f"No results found for '{item_name}' in '{city}'")
        raise HTTPException(status_code=404, detail=f"No prices found for {item_name} in {city}")
    
    # Special case handling for common searches
    if item_name in specific_search_cases:
        # Move specific items to the top of results
        priority_items = specific_search_cases[item_name]
        
        # Function to calculate item priority
        def get_item_priority(item):
            item_name_lower = item['item_name'].lower()
            
            # Check if this item exactly matches any of our priority items
            for i, priority_item in enumerate(priority_items):
                if item_name_lower.startswith(priority_item.lower()):
                    return i  # Return index as priority (lower is better)
                
            # Otherwise check regular priority rules
            if item_name_lower.startswith(item_name.lower()):
                return len(priority_items)  # After priority items
            elif any(word.lower().startswith(item_name.lower()) for word in item_name_lower.split()):
                return len(priority_items) + 1
            else:
                return len(priority_items) + 2
        
        # Sort with special handling
        sorted_results = sorted(results, key=get_item_priority)
    else:
        # Standard sorting for other searches
        sorted_results = sorted(results, key=lambda x: (
            0 if x['item_name'].lower().startswith(item_name.lower()) else
            1 if any(word.lower().startswith(item_name.lower()) for word in x['item_name'].split()) else
            2 if item_name.lower() in x['item_name'].lower() else
            3
        ))
    
    print(f"Found {len(sorted_results)} results for '{item_name}' in '{city}'")
    return sorted_results


# Add a new table for storing user carts
def init_cart_db():
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

init_cart_db()

# Model for saving a cart
class SaveCartRequest(BaseModel):
    cart_name: str
    email: str
    items: List[CartItem]

@app.post("/savecart")
def save_cart(cart: SaveCartRequest):
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    # Convert the list of items to a string for storage
    items_str = "|".join([f"{item.item_name}:{item.quantity}" for item in cart.items])
    
    cursor.execute("INSERT INTO carts (cart_name, email, items) VALUES (?, ?, ?)", (cart.cart_name, cart.email, items_str))
    conn.commit()
    conn.close()
    
    return {"message": "Cart saved successfully"}

@app.get("/savedcarts/{email}")
def get_saved_carts(email: str, city: str):
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    
    # Fetch both cart_name and items for the given email
    cursor.execute("SELECT cart_name, items FROM carts WHERE email = ?", (email,))
    records = cursor.fetchall()
    conn.close()
    
    if not records:
    # Return a 200 OK with an empty list for new or cart-less users
        return {
            "email": email,
            "saved_carts": []
        }
    
    # Convert the stored string back to a list of lists of items
    carts = []
    for record in records:
        cart_name = record[0]  # First item is cart_name
        items = [
            {"item_name": item.split(":")[0], "quantity": int(item.split(":")[1])}
            for item in record[1].split("|")
        ]
        
        # Get prices for each item in the cart
        for item in items:
            item_name = item["item_name"]
            prices_response = get_prices_by_item_and_city(city, item_name)  # Call the helper function
            
            # Get the lowest price
            if prices_response:
                item["price"] = min(prices_response, key=lambda x: x["price"])["price"]
            else:
                item["price"] = None
        
        carts.append({"cart_name": cart_name, "items": items})
    
    return {"email": email, "saved_carts": carts}






# Run the API server with:
# uvicorn api_server:app --reload

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
