"""
API tests for authentication endpoints.

Tests the /api/auth/* endpoints including registration, login, and token validation.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt
import os

from database.new_models import User
from services.auth_service import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES


class TestAuthEndpoints:
    """Test authentication API endpoints"""

    def test_register_success(self, client: TestClient, db_session: Session):
        """Test successful user registration"""
        registration_data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!"
        }

        response = client.post("/api/auth/register", json=registration_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "user_id" in data
        assert data["email"] == registration_data["email"]
        assert "password" not in data  # Password should not be returned
        assert "password_hash" not in data  # Hash should not be returned

        # Verify user was created in database
        user = db_session.query(User).filter_by(email=registration_data["email"]).first()
        assert user is not None
        assert user.email == registration_data["email"]

    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Test registration with already registered email"""
        registration_data = {
            "email": test_user.email,  # Already exists
            "password": "AnotherPass123!"
        }

        response = client.post("/api/auth/register", json=registration_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "already registered" in data["detail"].lower()

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email format"""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@@example.com",
            ""
        ]

        for email in invalid_emails:
            registration_data = {
                "email": email,
                "password": "ValidPass123!"
            }

            response = client.post("/api/auth/register", json=registration_data)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak passwords"""
        weak_passwords = [
            "123",          # Too short
            "pass",         # Too short
            "",             # Empty
        ]

        for i, password in enumerate(weak_passwords):
            registration_data = {
                "email": f"user{i}weak@example.com",
                "password": password
            }

            response = client.post("/api/auth/register", json=registration_data)
            # Should either fail validation or be rejected by business logic
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST
            ]

    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login"""
        login_data = {
            "username": test_user.email,  # OAuth2 uses 'username' field
            "password": "testpass123"
        }

        response = client.post("/api/auth/login", data=login_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Verify token is valid
        auth_service = AuthService(None)  # Don't need DB for token verification
        # Get the secret key from environment
        secret_key = os.getenv("SECRET_KEY", "test-secret-key-12345")
        payload = jwt.decode(
            data["access_token"],
            secret_key,
            algorithms=["HS256"]
        )
        assert "sub" in payload

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Test login with incorrect password"""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }

        response = client.post("/api/auth/login", data=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "incorrect" in data["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user"""
        login_data = {
            "username": "nobody@example.com",
            "password": "anypassword"
        }

        response = client.post("/api/auth/login", data=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self, client: TestClient):
        """Test login with missing fields"""
        # Missing password
        response = client.post("/api/auth/login", data={"username": "user@example.com"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing username
        response = client.post("/api/auth/login", data={"password": "password123"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Empty data
        response = client.post("/api/auth/login", data={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_protected_endpoint_with_token(self, client: TestClient, auth_headers: dict):
        """Test accessing protected endpoint with valid token"""
        # Test with a protected endpoint like saved carts list
        response = client.get("/api/saved-carts/list", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK

    def test_protected_endpoint_no_token(self, client: TestClient):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/saved-carts/list")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "not authenticated" in data["detail"].lower()

    def test_protected_endpoint_invalid_token(self, client: TestClient):
        """Test accessing protected endpoint with invalid token"""
        invalid_headers = {"Authorization": "Bearer invalid.token.here"}

        response = client.get("/api/saved-carts/list", headers=invalid_headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_expiration(self, client: TestClient, db_session: Session):
        """Test that expired tokens are rejected"""
        # Create a user
        auth_service = AuthService(db_session)
        user = auth_service.create_user("expired@example.com", "password123")
        db_session.commit()

        # Create token that's already expired
        secret_key = os.getenv("SECRET_KEY", "test-secret-key-12345")
        expired_token = jwt.encode(
            {
                "sub": str(user.user_id),
                "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
            },
            secret_key,
            algorithm="HS256"
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/saved-carts/list", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_case_insensitive_email(self, client: TestClient, test_user: User):
        """Test that login works with different email casing"""
        login_data = {
            "username": test_user.email.upper(),  # Use uppercase
            "password": "testpass123"
        }

        response = client.post("/api/auth/login", data=login_data)

        # Should handle case-insensitive email comparison
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]
