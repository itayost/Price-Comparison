import bcrypt
import jwt
import datetime
from typing import Dict, Any

# JWT configuration
SECRET_KEY = "iJJrwjxbCBE3OpbxKwexfmZLMCNlVkD1/LaA3o0Rx91e7dDkcd1ggiPctUjaYasY"  
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a stored password against one provided by user."""
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

def create_access_token(email: str) -> str:
    """Create a JWT token with user's email."""
    payload = {
        "sub": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)