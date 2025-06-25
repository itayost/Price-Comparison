# price_comparison_server/services/auth_service.py

from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
import jwt
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
import logging

from database.new_models import User

# Load environment variables
load_dotenv()

# Configure logging based on environment
logger = logging.getLogger(__name__)

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise ValueError("SECRET_KEY must be set in production environment")
    else:
        # Development fallback (with warning)
        SECRET_KEY = "dev-secret-key-do-not-use-in-production"
        logger.warning("Using default SECRET_KEY for development. Set SECRET_KEY in .env!")

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Password hashing configuration
# In production, you might want to increase rounds for better security
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12 if IS_PRODUCTION else 4  # Faster in development
)


class AuthService:
    """Service for handling authentication"""

    def __init__(self, db: Session):
        self.db = db

        # Log security settings (but not the actual secret!)
        logger.info(f"AuthService initialized in {ENVIRONMENT} mode")
        if not IS_PRODUCTION:
            logger.debug(f"Token expiry: {ACCESS_TOKEN_EXPIRE_MINUTES} minutes")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email.lower()).first()

    def create_user(self, email: str, password: str) -> User:
        """Create a new user"""
        # Normalize email
        email = email.lower().strip()

        # Check if user exists
        if self.get_user_by_email(email):
            raise ValueError("User with this email already exists")

        # Password strength check in production
        if IS_PRODUCTION:
            if len(password) < 8:
                raise ValueError("Password must be at least 8 characters in production")
            # Add more password rules as needed

        # Create new user
        hashed_password = self.get_password_hash(password)
        user = User(
            email=email,
            password_hash=hashed_password,
            created_at=datetime.utcnow()
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info(f"New user created: {email}")
        return user

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user"""
        user = self.get_user_by_email(email.lower())
        if not user:
            logger.debug(f"Authentication failed: User {email} not found")
            return None
        if not self.verify_password(password, user.password_hash):
            logger.debug(f"Authentication failed: Invalid password for {email}")
            return None

        logger.info(f"User authenticated: {email}")
        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()

        # Set expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        # Add token metadata
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),  # Issued at
            "env": ENVIRONMENT,  # Environment where token was issued
        })

        # Create token
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        logger.debug(f"Access token created for: {data.get('sub')}, expires: {expire}")
        return encoded_jwt

    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token (optional - for better security)"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "env": ENVIRONMENT,
        })

        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def verify_token(self, token: str, token_type: str = "access") -> Optional[str]:
        """Verify JWT token and return email"""
        try:
            # Decode token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            # Extract email
            email: str = payload.get("sub")
            if email is None:
                logger.warning("Token missing 'sub' claim")
                return None

            # Verify token type if specified
            if token_type == "refresh" and payload.get("type") != "refresh":
                logger.warning("Invalid token type")
                return None

            # Optional: Check if token was issued in same environment
            token_env = payload.get("env")
            if IS_PRODUCTION and token_env != "production":
                logger.warning(f"Development token used in production: {email}")
                # You might want to reject this in production

            return email

        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.JWTError as e:
            logger.debug(f"Token validation error: {e}")
            return None

    def revoke_token(self, token: str):
        """
        Revoke a token (optional - requires token blacklist implementation)
        This is a placeholder for token revocation logic
        """
        # In production, you might want to:
        # 1. Add token to a blacklist in Redis/Database
        # 2. Check blacklist in verify_token()
        if IS_PRODUCTION:
            logger.info(f"Token revocation requested (not implemented)")
        pass

    def get_current_user_from_token(self, token: str) -> Optional[User]:
        """Get user object from token"""
        email = self.verify_token(token)
        if email:
            return self.get_user_by_email(email)
        return None


# Utility functions for password strength (optional)
def check_password_strength(password: str) -> dict:
    """Check password strength and return feedback"""
    checks = {
        "length": len(password) >= 8,
        "has_upper": any(c.isupper() for c in password),
        "has_lower": any(c.islower() for c in password),
        "has_digit": any(c.isdigit() for c in password),
        "has_special": any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password)
    }

    strength = sum(checks.values())

    return {
        "checks": checks,
        "strength": strength,
        "is_strong": strength >= 4,
        "feedback": _get_password_feedback(checks)
    }


def _get_password_feedback(checks: dict) -> list:
    """Get password improvement suggestions"""
    feedback = []
    if not checks["length"]:
        feedback.append("Use at least 8 characters")
    if not checks["has_upper"]:
        feedback.append("Include uppercase letters")
    if not checks["has_lower"]:
        feedback.append("Include lowercase letters")
    if not checks["has_digit"]:
        feedback.append("Include numbers")
    if not checks["has_special"]:
        feedback.append("Include special characters")
    return feedback
