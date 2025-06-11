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