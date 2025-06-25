# price_comparison_server/services/auth_service.py

import os
import jwt
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import logging

from database.new_models import User

logger = logging.getLogger(__name__)

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


class AuthService:
    """Service for handling authentication and authorization"""

    def __init__(self, db: Session):
        self.db = db
        self.pwd_context = pwd_context

        # Log environment for debugging
        env = os.getenv("TESTING", "production")
        logger.info(f"AuthService initialized in {env} mode")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter_by(email=email).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter_by(user_id=user_id).first()

    def create_user(self, email: str, password: str) -> User:
        """Create a new user"""
        # Check if user already exists
        if self.get_user_by_email(email):
            raise ValueError("Email already registered")

        # Create new user
        user = User(
            email=email,
            password_hash=self.get_password_hash(password),
            created_at=datetime.utcnow()
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info(f"New user created: {email}")
        return user

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user"""
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not self.verify_password(password, user.password_hash):
            return None

        logger.info(f"User authenticated: {email}")
        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create a JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "env": os.getenv("TESTING", "production")  # Add environment to token
        })

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[str]:
        """Verify and decode a JWT token - returns email"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                return None
            return email
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.PyJWTError as e:  # Fixed: Use PyJWTError instead of JWTError
            logger.warning(f"Invalid token: {e}")
            return None

    def get_current_user_from_token(self, token: str) -> Optional[User]:
        """Get user from JWT token"""
        email = self.verify_token(token)
        if not email:
            return None

        user = self.get_user_by_email(email)
        return user

    def update_user_password(self, user: User, new_password: str) -> None:
        """Update user password"""
        user.password_hash = self.get_password_hash(new_password)
        self.db.commit()
        logger.info(f"Password updated for user: {user.email}")

    def delete_user(self, user_id: int) -> bool:
        """Delete a user account"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        self.db.delete(user)
        self.db.commit()
        logger.info(f"User deleted: {user.email}")
        return True
