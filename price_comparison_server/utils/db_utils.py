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