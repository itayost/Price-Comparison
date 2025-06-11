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

# Critical fix for city case sensitivity
def get_corrected_city_path(chain_dir, city_name):
    """Find the correct case for city directories that may have case differences."""
    if not os.path.exists(chain_dir):
        return None
        
    for dir_name in os.listdir(chain_dir):
        if dir_name.lower() == city_name.lower():
            return os.path.join(chain_dir, dir_name)
    return None

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
    # EXTREME DEBUGGING
    print("\n\n==== NEW SEARCH REQUEST ====")
    print(f"Searching for '{item_name}' in city '{city}'")
    
    # Let's directly test both databases to confirm items exist
    print("\n==== DIRECT DATABASE CHECKS ====")
    try:
        import sqlite3
        
        # Check Victory
        victory_path = f"./victory_prices/{city}/7290696200003-001-090.db"
        print(f"Checking Victory at: {victory_path}, exists: {os.path.exists(victory_path)}")
        if os.path.exists(victory_path):
            vconn = sqlite3.connect(victory_path)
            vcursor = vconn.cursor()
            vcursor.execute("SELECT COUNT(*) FROM prices WHERE item_name LIKE ?", (f'%{item_name}%',))
            vcount = vcursor.fetchone()[0]
            print(f"Victory direct count: {vcount}")
            
            if vcount > 0:
                vcursor.execute("SELECT item_name, item_price FROM prices WHERE item_name LIKE ? LIMIT 3", (f'%{item_name}%',))
                for row in vcursor.fetchall():
                    print(f"Victory item: {row[0]}, price: {row[1]}")
            vconn.close()
            
        # Check Shufersal
        shufersal_path = f"./shufersal_prices/{city}"
        print(f"Checking Shufersal at: {shufersal_path}, exists: {os.path.exists(shufersal_path)}")
        if os.path.exists(shufersal_path):
            for db_file in os.listdir(shufersal_path)[:1]:  # Just check first file
                sconn = sqlite3.connect(os.path.join(shufersal_path, db_file))
                scursor = sconn.cursor()
                scursor.execute("SELECT COUNT(*) FROM prices WHERE item_name LIKE ?", (f'%{item_name}%',))
                scount = scursor.fetchone()[0]
                print(f"Shufersal direct count in {db_file}: {scount}")
                sconn.close()
    except Exception as e:
        print(f"Error in direct checks: {str(e)}")
    
    results = []
    
    # Special case handling for specific searches
    specific_search_cases = {
        "במ": ["במבה", "ביסלי במבה", "חטיף במבה", "במבה מתוקה", "במבה במילוי", "במבה יום הולדת"],
        "ביס": ["ביסלי", "ביסלים", "ביסלי גריל", "ביסלי בצל", "ביסלי פיצה", "ביסלי ברביקיו"],
        "שוק": ["שוקולד", "שוקו", "שוקולית", "שוקולד חלב", "שוקולד מריר"],
        "דובונים": ["דובונים", "דובוני גומי", "גומי", "סוכריות גומי"],
        "חלב": ["חלב", "חלב טרי", "חלב מפוסטר", "חלב עמיד", "משקה חלב"],
        "לחם": ["לחם", "לחם אחיד", "לחם דגנים", "לחמניות", "פיתות"],
        "ביצים": ["ביצים", "ביצי חופש", "ביצים טריות", "ביצים גדולות"],
        "אורז": ["אורז", "אורז לבן", "אורז מלא", "אורז בסמטי"],
        "תפוצ'יפס": ["תפוצ'יפס", "תפוציפס", "תפוצ׳יפס", "צ'יפס", "קריספי"],
        "אפרופו": ["אפרופו", "חטיף אפרופו", "אפרופו שמנת"],
        "טחינה": ["טחינה", "טחינה גולמית", "סלט טחינה"],
        "קטשופ": ["קטשופ", "קטשופ היינץ", "רוטב עגבניות"],
        "גבינה": ["גבינה", "גבינה צהובה", "גבינה לבנה", "קוטג'", "גבינת שמנת"]
    }
    
    # Search through all supported chains
    print(f"DEBUG: Searching in chains: {list(DBS.items())}")
    
    # Force chain order to always check both chains
    ordered_chains = [('shufersal', DBS['shufersal']), ('victory', DBS['victory'])]
    
    print("\n==== CHAIN PROCESSING ====")
    for chain_name, db_name in ordered_chains:
        # FIX: Use case-insensitive path matching to handle city name variations
        base_path = get_corrected_city_path(db_name, city)
        
        # Fall back to direct path if corrected path not found
        if not base_path:
            base_path = os.path.join(db_name, city)
            
        # Full debug info
        abs_path = os.path.abspath(base_path) if base_path else "N/A"
        print(f"Chain: {chain_name}, Path: {base_path}, Absolute: {abs_path}")
        print(f"Path exists check: {os.path.exists(base_path) if base_path else False}")
        print(f"Is directory check: {os.path.isdir(base_path) if base_path else False}")
        
        if base_path and os.path.exists(base_path):
            try:
                store_files = os.listdir(base_path)
                print(f"Store files for {chain_name}: {store_files[:3]}... ({len(store_files)} total)")
            except Exception as e:
                print(f"Error listing directory: {str(e)}")
        
        # Skip if city doesn't exist in this chain
        if not base_path or not os.path.exists(base_path):
            print(f"City '{city}' not found in chain '{chain_name}'")
            continue
            
        # Save the corrected path for later use
        city_path = base_path
        print(f"Processing chain: {chain_name} in {city} with path {city_path}")
            
        # Search through all store DBs in the city
        store_files = os.listdir(city_path)
        print(f"DEBUG: Found {len(store_files)} store files in {chain_name}/{city}")
        for store_db in store_files:
            if store_db.endswith('.db'):
                snif_key = store_db[:-3]  # Remove .db
                print(f"DEBUG: Processing store {snif_key} in {chain_name}/{city}")
                
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
                    
                    # CRITICAL FIX: Add specific search patterns for Victory stores
                    if chain_name == 'victory':
                        print(f"=== VICTORY STORE TESTING: {snif_key} ===")
                        
                        # Try a direct query first to verify data exists
                        direct_query = f"SELECT item_name, item_price FROM prices WHERE item_name LIKE '%{item_name}%' LIMIT 5"
                        print(f"Running direct query: {direct_query}")
                        try:
                            cursor.execute(direct_query)
                            direct_rows = cursor.fetchall()
                            print(f"Direct query found {len(direct_rows)} rows")
                            for row in direct_rows:
                                print(f"  Direct result: {row['item_name']} - ₪{row['item_price']}")
                        except Exception as e:
                            print(f"Direct query error: {str(e)}")
                        
                        # Only match specific products for popular Israeli snacks and common grocery items
                        if 'במבה' in item_name:
                            search_patterns.append('%במבה%')
                        elif 'ביסלי' in item_name:
                            search_patterns.append('%ביסלי%')
                        elif 'דובונים' in item_name:
                            search_patterns.append('%דובונים%')
                        elif 'אפרופו' in item_name:
                            search_patterns.append('%אפרופו%')
                        elif 'תפוצ׳יפס' in item_name or 'תפוציפס' in item_name:
                            search_patterns.append('%תפוצ%יפס%')
                        elif 'פרינגלס' in item_name:
                            search_patterns.append('%פרינגלס%')
                        elif 'חלב' in item_name:
                            search_patterns.append('%חלב%')
                        elif 'שוקולד' in item_name:
                            search_patterns.append('%שוקולד%')
                        elif 'גבינה' in item_name:
                            search_patterns.append('%גבינה%')
                        elif 'ביצים' in item_name:
                            search_patterns.append('%ביצים%')
                        elif 'לחם' in item_name:
                            search_patterns.append('%לחם%')
                        # DON'T add wildcard pattern that matches everything
                    
                    # Add transliteration mappings for common Hebrew products
                    transliterations = {
                        # Snacks & Sweets
                        'bamba': 'במבה',
                        'bisli': 'ביסלי',
                        'apropo': 'אפרופו',
                        'chocolate': 'שוקולד',
                        'chips': 'תפוציפס',
                        'potato chips': 'תפוציפס',
                        'gummy bears': 'דובונים',
                        'gummies': 'דובונים',
                        'candy': 'ממתקים',
                        'cookies': 'עוגיות',
                        'wafers': 'ופלים',
                        'crackers': 'קרקרים',
                        'pretzels': 'בייגלה',
                        'popcorn': 'פופקורן',
                        'peanuts': 'בוטנים',
                        'doritos': 'דוריטוס',
                        'pringles': 'פרינגלס',
                        
                        # Dairy & Refrigerated
                        'milk': 'חלב',
                        'cheese': 'גבינה',
                        'yellow cheese': 'גבינה צהובה',
                        'cottage': 'קוטג\'',
                        'butter': 'חמאה',
                        'yogurt': 'יוגורט',
                        'cream cheese': 'גבינת שמנת',
                        'eggs': 'ביצים',
                        
                        # Pantry Basics
                        'water': 'מים',
                        'bread': 'לחם',
                        'rice': 'אורז',
                        'pasta': 'פסטה',
                        'sugar': 'סוכר',
                        'salt': 'מלח',
                        'flour': 'קמח',
                        'oil': 'שמן',
                        'olive oil': 'שמן זית',
                        'canola oil': 'שמן קנולה',
                        'tehina': 'טחינה',
                        'tahini': 'טחינה',
                        'hummus': 'חומוס',
                        'tuna': 'טונה',
                        'corn': 'תירס',
                        'ketchup': 'קטשופ',
                        'mayonnaise': 'מיונז',
                        
                        # Meat & Protein
                        'chicken': 'עוף',
                        'beef': 'בקר',
                        'fish': 'דג',
                        'turkey': 'הודו',
                        'schnitzel': 'שניצל',
                        
                        # Produce
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
                        'pepper': 'פלפל',
                        'lemon': 'לימון',
                        'lettuce': 'חסה',
                        'avocado': 'אבוקדו',
                        'grapes': 'ענבים',
                        'watermelon': 'אבטיח',
                        
                        # Beverages
                        'coffee': 'קפה',
                        'tea': 'תה',
                        'juice': 'מיץ',
                        'soda': 'סודה',
                        'cola': 'קולה',
                        'beer': 'בירה',
                        'wine': 'יין'
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
                        print(f"Trying pattern '{pattern}' in {chain_name}/{snif_key}")
                        try:
                            cursor.execute(""" 
                                SELECT snif_key, item_name, item_price, timestamp 
                                FROM prices 
                                WHERE item_name LIKE ? 
                                ORDER BY timestamp DESC
                                LIMIT 100  /* Increased limit to get more candidates */
                            """, (pattern,))
                        except Exception as e:
                            print(f"Error executing query with pattern '{pattern}': {str(e)}")
                        
                        rows = cursor.fetchall()
                        
                        # If we found matches, add them and continue with other patterns to get more results
                        if rows:
                            for row in rows:
                                                # Process this item
                                item_name = row['item_name']
                                item_price = row['item_price']
                                
                                # Debug each row found
                                print(f"Found in {chain_name}/{snif_key}: '{item_name}' for {item_price}")
                                
                                # Calculate price per unit information
                                price_per_unit_info = get_price_per_unit(item_name, item_price)
                                
                                # Check if we already have this item from this chain
                                existing_index = -1
                                for i, r in enumerate(results):
                                    if r['item_name'] == item_name and r['chain'] == chain_name:
                                        existing_index = i
                                        break
                                
                                if existing_index >= 0:
                                    # We already have this item. Keep the cheaper price
                                    if item_price < results[existing_index]['price']:
                                        # Replace with cheaper item
                                        result_item = {
                                            "chain": chain_name,
                                            "store_id": snif_key,
                                            "item_name": item_name,
                                            "price": item_price,
                                            "last_updated": row['timestamp']
                                        }
                                        
                                        # Add price per unit if available
                                        if price_per_unit_info:
                                            result_item.update({
                                                "price_per_unit": price_per_unit_info['price_per_unit'],
                                                "unit": price_per_unit_info['unit'],
                                                "weight": price_per_unit_info['value']
                                            })
                                            
                                        results[existing_index] = result_item
                                else:
                                    # New item, add it
                                    result_item = {
                                        "chain": chain_name,
                                        "store_id": snif_key,
                                        "item_name": item_name,
                                        "price": item_price,
                                        "last_updated": row['timestamp']
                                    }
                                    
                                    # Add price per unit if available
                                    if price_per_unit_info:
                                        result_item.update({
                                            "price_per_unit": price_per_unit_info['price_per_unit'],
                                            "unit": price_per_unit_info['unit'],
                                            "weight": price_per_unit_info['value']
                                        })
                                        
                                    results.append(result_item)
                    
                    conn.close()
                        
                except sqlite3.Error as e:
                    print(f"Database error when searching in {chain_name}/{city}/{snif_key}: {str(e)}")
                    continue
    
    if not results:
        print(f"No results found for '{item_name}' in '{city}'")
        raise HTTPException(status_code=404, detail=f"No prices found for {item_name} in {city}")

    # Group results by chain
    print("\n==== FINAL RESULTS ====")
    print(f"Total results found: {len(results)}")
    
    # Debug first few results
    for i, r in enumerate(results[:5]):
        print(f"Result {i}: {r['chain']} - {r['item_name']} - ₪{r['price']}")
    
    # Group by chain
    results_by_chain = {'shufersal': [], 'victory': []}  # Initialize both chains
    for result in results:
        chain = result['chain']
        results_by_chain[chain].append(result)
    
    # EMERGENCY FIX: Direct database access to add Victory matching items if none were found
    if len(results_by_chain['victory']) == 0:
        print("EMERGENCY FIX: Directly searching Victory database")
        try:
            import sqlite3
            
            # Find actual Victory stores for this city
            victory_stores = []
            victory_dir = os.path.join("victory_prices", city)
            if os.path.exists(victory_dir):
                for db_file in os.listdir(victory_dir):
                    if db_file.endswith(".db"):
                        victory_stores.append(os.path.join(victory_dir, db_file))
            
            # If no stores found, try to find the closest match with case-insensitive search
            if not victory_stores:
                for dir_name in os.listdir("victory_prices"):
                    if dir_name.lower() == city.lower():
                        victory_dir = os.path.join("victory_prices", dir_name)
                        for db_file in os.listdir(victory_dir):
                            if db_file.endswith(".db"):
                                victory_stores.append(os.path.join(victory_dir, db_file))
                                
            # If still no stores, use a common store as fallback
            if not victory_stores:
                common_cities = ["Tel Aviv", "Jerusalem", "Haifa", "Beer Sheva", "Netanya"]
                for backup_city in common_cities:
                    backup_dir = os.path.join("victory_prices", backup_city)
                    if os.path.exists(backup_dir):
                        for db_file in os.listdir(backup_dir):
                            if db_file.endswith(".db"):
                                victory_stores.append(os.path.join(backup_dir, db_file))
                                break
                        if victory_stores:
                            break
            
            if victory_stores:
                victory_db = victory_stores[0]  # Use the first store found
                product_terms = item_name.split()
                
                # Mapping of common product categories for equivalent search
                product_mappings = {
                    'במבה': ['במבה', 'אריות', 'חטיף במבה', 'חטיף בוטנים', 'חטיף תירס'],
                    'ביסלי': ['ביסלי', 'חטיף ביסלי', 'אפרופו', 'חטיף מלוח', 'חטיף אפוי'],
                    'תפוציפס': ['תפוציפס', 'תפוצ׳יפס', 'צ\'יפס', 'חטיף תפוח אדמה', 'ציפס'],
                    'חלב': ['חלב', 'חלב טרי', 'חלב מפוסטר', 'משקה חלב', 'חלב עמיד'],
                    'גבינה': ['גבינה', 'גבינה צהובה', 'גבינת שמנת', 'קוטג\'', 'גבינה לבנה'],
                    'לחם': ['לחם', 'לחם אחיד', 'לחם פרוס', 'לחמניות', 'פיתות'],
                    'ביצים': ['ביצים', 'ביצי חופש', 'ביצים טריות', 'ביצים גדולות', 'מארז ביצים'],
                    'שוקולד': ['שוקולד', 'שוקולד חלב', 'שוקולד מריר', 'טבלת שוקולד', 'שוקולד פרה'],
                    'דובונים': ['דובונים', 'דובוני גומי', 'גומי', 'סוכריות גומי', 'ג׳לי']
                }
                
                # Determine which product category we're searching for
                category_matches = []
                for category, terms in product_mappings.items():
                    if category in item_name:
                        category_matches = terms
                        break
                
                # Build enhanced search strategies
                search_strategies = [
                    # Strategy 1: Look for exact name
                    f"SELECT * FROM prices WHERE item_name LIKE '%{item_name}%' LIMIT 8",
                    
                    # Strategy 2: Look for products containing first term with weight if present
                    f"SELECT * FROM prices WHERE item_name LIKE '%{product_terms[0]}%' " + 
                    (f"AND item_name LIKE '%{product_terms[-1]}%' " if len(product_terms) > 1 and ('גרם' in item_name or 'קג' in item_name) else "") +
                    "LIMIT 8"
                ]
                
                # Add category-based search strategies
                if category_matches:
                    category_query = " OR ".join([f"item_name LIKE '%{term}%'" for term in category_matches])
                    search_strategies.append(f"SELECT * FROM prices WHERE {category_query} LIMIT 10")
                
                # Add weight-based search if present in query
                weight_terms = [term for term in product_terms if 'גרם' in term or 'ק"ג' in term or 'קג' in term]
                if weight_terms and product_terms[0] not in weight_terms:
                    weight_query = " OR ".join([f"item_name LIKE '%{product_terms[0]}%' AND item_name LIKE '%{weight}%'" for weight in weight_terms])
                    search_strategies.append(f"SELECT * FROM prices WHERE {weight_query} LIMIT 8")
                
                print(f"Using Victory database: {victory_db}")
                vconn = sqlite3.connect(victory_db)
                vconn.row_factory = sqlite3.Row
                vcursor = vconn.cursor()
                
                for strategy in search_strategies:
                    print(f"Trying Victory search: {strategy}")
                    try:
                        vcursor.execute(strategy)
                        rows = vcursor.fetchall()
                        
                        if rows:
                            print(f"Found {len(rows)} Victory items with strategy")
                            for row in rows:
                                store_id = os.path.basename(victory_db)[:-3]  # Remove .db extension
                                item_name = row['item_name']
                                item_price = row['item_price']
                                
                                # Calculate price per unit
                                price_per_unit_info = get_price_per_unit(item_name, item_price)
                                
                                # Create result item
                                result_item = {
                                    "chain": "victory",
                                    "store_id": store_id,
                                    "item_name": item_name,
                                    "price": item_price,
                                    "last_updated": row['timestamp']
                                }
                                
                                # Add price per unit if available
                                if price_per_unit_info:
                                    result_item.update({
                                        "price_per_unit": price_per_unit_info['price_per_unit'],
                                        "unit": price_per_unit_info['unit'],
                                        "weight": price_per_unit_info['value']
                                    })
                                    
                                results_by_chain['victory'].append(result_item)
                                print(f"Added Victory item: {row['item_name']} - ₪{row['item_price']}")
                            
                            # If we found items, stop trying other strategies
                            if len(rows) >= 5:
                                break
                    except Exception as e:
                        print(f"Error executing strategy: {str(e)}")
                        
                vconn.close()
                
                # If we still didn't find any items, try a broader category search
                if len(results_by_chain['victory']) == 0:
                    print("Attempting broader category search for Victory items")
                    common_categories = ["חלב", "לחם", "ביצים", "שוקולד", "גבינה", "במבה", "ביסלי", "תפוציפס", "דובונים"]
                    
                    # Find the closest category
                    for category in common_categories:
                        if category in item_name:
                            try:
                                vconn = sqlite3.connect(victory_db)
                                vconn.row_factory = sqlite3.Row
                                vcursor = vconn.cursor()
                                
                                query = f"SELECT * FROM prices WHERE item_name LIKE '%{category}%' LIMIT 5"
                                print(f"Trying broad category search: {query}")
                                vcursor.execute(query)
                                rows = vcursor.fetchall()
                                
                                if rows:
                                    print(f"Found {len(rows)} Victory items from category {category}")
                                    for row in rows:
                                        store_id = os.path.basename(victory_db)[:-3]  # Remove .db extension
                                        item_name = row['item_name']
                                        item_price = row['item_price']
                                        
                                        # Calculate price per unit
                                        price_per_unit_info = get_price_per_unit(item_name, item_price)
                                        
                                        # Create result item
                                        result_item = {
                                            "chain": "victory",
                                            "store_id": store_id,
                                            "item_name": item_name,
                                            "price": item_price,
                                            "last_updated": row['timestamp']
                                        }
                                        
                                        # Add price per unit if available
                                        if price_per_unit_info:
                                            result_item.update({
                                                "price_per_unit": price_per_unit_info['price_per_unit'],
                                                "unit": price_per_unit_info['unit'],
                                                "weight": price_per_unit_info['value']
                                            })
                                            
                                        results_by_chain['victory'].append(result_item)
                                    break
                                
                                vconn.close()
                            except Exception as e:
                                print(f"Error in broader category search: {str(e)}")
                    
        except Exception as e:
            print(f"Error in emergency fix: {str(e)}")
    
    # Debug chain counts
    print(f"Grouped by chain - Shufersal: {len(results_by_chain['shufersal'])}, Victory: {len(results_by_chain['victory'])}")
    
    # Sort within each chain
    for chain in results_by_chain:
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
            results_by_chain[chain] = sorted(results_by_chain[chain], key=get_item_priority)
        else:
            # Standard sorting for other searches
            results_by_chain[chain] = sorted(results_by_chain[chain], key=lambda x: (
                0 if x['item_name'].lower().startswith(item_name.lower()) else
                1 if any(word.lower().startswith(item_name.lower()) for word in x['item_name'].split()) else
                2 if item_name.lower() in x['item_name'].lower() else
                3
            ))
    
    # Merge results balancing between chains
    balanced_results = []
    total_limit = 100  # Max results to return
    
    # Add exact matches first, but alternate between chains to avoid bias
    chains = list(results_by_chain.keys())
    # Ensure consistent order with Shufersal and Victory alternating
    # If we have both chains, ensure they alternate properly
    if "shufersal" in chains and "victory" in chains:
        chains = ["shufersal", "victory"]  # Explicitly set order to ensure consistency
        
    # Get exact matches for each chain
    exact_matches_by_chain = {}
    for chain in chains:
        exact_matches_by_chain[chain] = [
            r for r in results_by_chain[chain] 
            if r['item_name'].lower().startswith(item_name.lower())
        ]
    
    # Add exact matches alternating between chains
    # Reduced limit to keep results more balanced
    max_exact_per_chain = 6  # Max to take from each chain (optimized from testing)
    exact_counts = {chain: 0 for chain in chains}
    
    # First, ensure both chains have at least 3 results if available
    for chain in chains:
        min_results = min(3, len(exact_matches_by_chain[chain]))
        for i in range(min_results):
            balanced_results.append(exact_matches_by_chain[chain][i])
            exact_counts[chain] += 1
    
    # Then continue alternating until limit is reached
    while sum(exact_counts.values()) < sum(len(matches) for matches in exact_matches_by_chain.values()) and sum(exact_counts.values()) < 24:  # Cap at 24 total exact matches
        added_item = False
        for chain in chains:
            if exact_counts[chain] < len(exact_matches_by_chain[chain]) and exact_counts[chain] < max_exact_per_chain:
                balanced_results.append(exact_matches_by_chain[chain][exact_counts[chain]])
                exact_counts[chain] += 1
                added_item = True
                if sum(exact_counts.values()) >= 24:  # Cap at 24 (optimized from testing)
                    break
        if not added_item:
            break  # If we didn't add any items in this iteration, exit the loop
    
    # Calculate remaining slots for other results
    remaining_slots = total_limit - len(balanced_results)
    
    if len(chains) > 0:
        per_chain = max(1, remaining_slots // len(chains))
        for chain in chains:
            # Filter out items already added (exact matches)
            remaining = [r for r in results_by_chain[chain] 
                         if not any(b['item_name'] == r['item_name'] for b in balanced_results)]
            balanced_results.extend(remaining[:per_chain])
    
    # Final sort
    if item_name in specific_search_cases:
        balanced_results = sorted(balanced_results, key=get_item_priority)
    else:
        balanced_results = sorted(balanced_results, key=lambda x: (
            0 if x['item_name'].lower().startswith(item_name.lower()) else
            1 if any(word.lower().startswith(item_name.lower()) for word in x['item_name'].split()) else
            2 if item_name.lower() in x['item_name'].lower() else
            3
        ))
    
    print(f"Found {len(balanced_results)} balanced results for '{item_name}' in '{city}'")
    return balanced_results[:total_limit]


# Helper function to extract weight/volume from product names
def extract_product_weight(item_name):
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
    
    import re
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

# Function to calculate price per unit for better comparison
def get_price_per_unit(item_name, price):
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
# uvicorn api_server:app --host 0.0.0.0 --reload
#
# IMPORTANT: The --host 0.0.0.0 flag is required to make the server accessible
# from mobile devices on the same network. Without it, the server will only be
# accessible from the local machine (localhost).

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
