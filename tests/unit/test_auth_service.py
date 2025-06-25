"""
Unit tests for authentication service.

Tests user registration, login, JWT token generation and validation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import jwt

from services.auth_service import AuthService
from database.new_models import User
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


class TestAuthService:
    """Test AuthService functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_db = Mock(spec=Session)
        self.auth_service = AuthService(self.mock_db)
    
    def test_create_user_success(self):
        """Test successful user creation"""
        email = "newuser@example.com"
        password = "securepass123"
        
        # Mock the database operations
        self.mock_db.query().filter_by().first.return_value = None
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        self.mock_db.refresh = Mock()
        
        # Create user
        user = self.auth_service.create_user(email, password)
        
        # Assertions
        assert user.email == email
        assert user.password_hash != password  # Password should be hashed
        assert self.auth_service.verify_password(password, user.password_hash)
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
    
    def test_create_duplicate_user(self):
        """Test that duplicate email raises exception"""
        email = "existing@example.com"
        
        # Mock existing user
        existing_user = User(email=email, password_hash="hash")
        self.mock_db.query().filter_by().first.return_value = existing_user
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Email already registered"):
            self.auth_service.create_user(email, "password123")
    
    def test_authenticate_user_success(self):
        """Test successful user authentication"""
        email = "user@example.com"
        password = "correctpass"
        hashed = self.auth_service.get_password_hash(password)
        
        # Mock user
        mock_user = User(
            user_id=1,
            email=email,
            password_hash=hashed
        )
        self.mock_db.query().filter_by().first.return_value = mock_user
        
        # Authenticate
        user = self.auth_service.authenticate_user(email, password)
        
        assert user is not None
        assert user.email == email
    
    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password"""
        email = "user@example.com"
        correct_password = "correctpass"
        wrong_password = "wrongpass"
        
        # Mock user with correct password hash
        mock_user = User(
            email=email,
            password_hash=self.auth_service.get_password_hash(correct_password)
        )
        self.mock_db.query().filter_by().first.return_value = mock_user
        
        # Should return None for wrong password
        user = self.auth_service.authenticate_user(email, wrong_password)
        assert user is None
    
    def test_authenticate_nonexistent_user(self):
        """Test authentication with non-existent user"""
        self.mock_db.query().filter_by().first.return_value = None
        
        user = self.auth_service.authenticate_user("nobody@example.com", "pass")
        assert user is None
    
    def test_create_access_token(self):
        """Test JWT token creation"""
        user_id = 123
        
        # Create token
        token = self.auth_service.create_access_token(user_id)
        
        # Decode and verify
        payload = jwt.decode(
            token,
            self.auth_service.secret_key,
            algorithms=[self.auth_service.algorithm]
        )
        
        assert payload["sub"] == str(user_id)
        assert "exp" in payload
        
        # Check expiration is set correctly (30 days)
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + timedelta(days=30)
        
        # Allow 1 minute difference for test execution time
        assert abs((exp_time - expected_exp).total_seconds()) < 60
    
    def test_create_access_token_custom_expiry(self):
        """Test token creation with custom expiry"""
        user_id = 456
        expires_delta = timedelta(hours=1)
        
        token = self.auth_service.create_access_token(user_id, expires_delta)
        
        payload = jwt.decode(
            token,
            self.auth_service.secret_key,
            algorithms=[self.auth_service.algorithm]
        )
        
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + expires_delta
        
        assert abs((exp_time - expected_exp).total_seconds()) < 60
    
    def test_verify_token_valid(self):
        """Test verification of valid token"""
        user_id = 789
        token = self.auth_service.create_access_token(user_id)
        
        # Mock user lookup
        mock_user = User(user_id=user_id, email="user@example.com")
        self.mock_db.query().filter_by().first.return_value = mock_user
        
        # Verify token
        user = self.auth_service.verify_token(token)
        
        assert user is not None
        assert user.user_id == user_id
    
    def test_verify_token_expired(self):
        """Test verification of expired token"""
        user_id = 999
        
        # Create expired token
        expired_token = self.auth_service.create_access_token(
            user_id,
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        # Should return None for expired token
        user = self.auth_service.verify_token(expired_token)
        assert user is None
    
    def test_verify_token_invalid(self):
        """Test verification of invalid token"""
        # Create token with wrong secret
        wrong_secret = "wrong_secret_key"
        payload = {
            "sub": "123",
            "exp": datetime.utcnow() + timedelta(days=1)
        }
        invalid_token = jwt.encode(payload, wrong_secret, algorithm="HS256")
        
        # Should return None for invalid token
        user = self.auth_service.verify_token(invalid_token)
        assert user is None
    
    def test_verify_token_malformed(self):
        """Test verification of malformed token"""
        malformed_tokens = [
            "not.a.token",
            "invalidbase64",
            "",
            None
        ]
        
        for token in malformed_tokens:
            user = self.auth_service.verify_token(token)
            assert user is None
    
    def test_verify_token_user_not_found(self):
        """Test token verification when user doesn't exist"""
        user_id = 404
        token = self.auth_service.create_access_token(user_id)
        
        # Mock user not found
        self.mock_db.query().filter_by().first.return_value = None
        
        # Should return None when user not found
        user = self.auth_service.verify_token(token)
        assert user is None
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        passwords = [
            "simple123",
            "C0mpl3x!P@ssw0rd",
            "עברית123",  # Hebrew characters
            "🔐🔑💻",  # Emojis
            "a" * 100  # Long password
        ]
        
        for password in passwords:
            # Hash password
            hashed = self.auth_service.get_password_hash(password)
            
            # Verify correct password
            assert self.auth_service.verify_password(password, hashed)
            
            # Verify wrong password fails
            assert not self.auth_service.verify_password(password + "wrong", hashed)
            
            # Ensure hash is different from original
            assert hashed != password
            
            # Ensure same password creates different hashes (due to salt)
            hashed2 = self.auth_service.get_password_hash(password)
            assert hashed != hashed2
    
    def test_get_user_by_id(self):
        """Test getting user by ID"""
        user_id = 123
        mock_user = User(user_id=user_id, email="found@example.com")
        
        self.mock_db.query().filter_by().first.return_value = mock_user
        
        user = self.auth_service.get_user_by_id(user_id)
        
        assert user is not None
        assert user.user_id == user_id
        assert user.email == "found@example.com"
    
    def test_get_user_by_email(self):
        """Test getting user by email"""
        email = "search@example.com"
        mock_user = User(user_id=456, email=email)
        
        self.mock_db.query().filter_by().first.return_value = mock_user
        
        user = self.auth_service.get_user_by_email(email)
        
        assert user is not None
        assert user.email == email
    
    @patch('services.auth_service.datetime')
    def test_token_expiry_edge_cases(self, mock_datetime):
        """Test token expiry edge cases"""
        # Mock current time
        current_time = datetime(2025, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        mock_datetime.fromtimestamp = datetime.fromtimestamp
        
        user_id = 111
        
        # Test with None expiry (should use default)
        token = self.auth_service.create_access_token(user_id, None)
        payload = jwt.decode(
            token,
            self.auth_service.secret_key,
            algorithms=[self.auth_service.algorithm]
        )
        
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_exp = current_time + timedelta(days=30)
        assert abs((exp_time - expected_exp).total_seconds()) < 60
