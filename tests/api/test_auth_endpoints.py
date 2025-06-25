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

from database.new_models import User
from services.auth_service import AuthService


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
            "password",     # No numbers
            "12345678",     # No letters
            "",             # Empty
        ]
        
        for password in weak_passwords:
            registration_data = {
                "email": f"user{password}@example.com",
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
        payload = jwt.decode(
            data["access_token"],
            auth_service.secret_key,
            algorithms=[auth_service.algorithm]
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
    
    def test_get_current_user(self, client: TestClient, auth_headers: dict):
        """Test getting current user information"""
        response = client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "user_id" in data
        assert "email" in data
        assert data["email"] == "testuser@example.com"
    
    def test_get_current_user_no_token(self, client: TestClient):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "not authenticated" in data["detail"].lower()
    
    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test accessing protected endpoint with invalid token"""
        invalid_headers = {"Authorization": "Bearer invalid.token.here"}
        
        response = client.get("/api/auth/me", headers=invalid_headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_expired_token(self, client: TestClient, db_session: Session):
        """Test accessing protected endpoint with expired token"""
        # Create a user and generate expired token
        auth_service = AuthService(db_session)
        user = auth_service.create_user("expired@example.com", "password123")
        db_session.commit()
        
        # Create token that's already expired
        expired_token = auth_service.create_access_token(
            user.user_id,
            expires_delta=timedelta(seconds=-1)
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token(self, client: TestClient, auth_headers: dict):
        """Test refreshing access token"""
        response = client.post("/api/auth/refresh", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # New token should be different from the old one
        old_token = auth_headers["Authorization"].split(" ")[1]
        assert data["access_token"] != old_token
    
    def test_logout(self, client: TestClient, auth_headers: dict):
        """Test logout endpoint"""
        response = client.post("/api/auth/logout", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "success" in data["message"].lower()
    
    def test_change_password(self, client: TestClient, auth_headers: dict, db_session: Session):
        """Test changing user password"""
        password_data = {
            "current_password": "testpass123",
            "new_password": "NewSecurePass456!"
        }
        
        response = client.post("/api/auth/change-password", json=password_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        
        # Verify can login with new password
        login_data = {
            "username": "testuser@example.com",
            "password": password_data["new_password"]
        }
        
        login_response = client.post("/api/auth/login", data=login_data)
        assert login_response.status_code == status.HTTP_200_OK
    
    def test_change_password_wrong_current(self, client: TestClient, auth_headers: dict):
        """Test changing password with wrong current password"""
        password_data = {
            "current_password": "wrongcurrent",
            "new_password": "NewSecurePass456!"
        }
        
        response = client.post("/api/auth/change-password", json=password_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "incorrect" in data["detail"].lower()
    
    def test_delete_account(self, client: TestClient, auth_headers: dict, db_session: Session):
        """Test account deletion"""
        # Create a user specifically for deletion
        auth_service = AuthService(db_session)
        user_to_delete = auth_service.create_user("delete@example.com", "deletepass123")
        db_session.commit()
        
        # Login as the user to delete
        login_response = client.post("/api/auth/login", data={
            "username": "delete@example.com",
            "password": "deletepass123"
        })
        token = login_response.json()["access_token"]
        delete_headers = {"Authorization": f"Bearer {token}"}
        
        # Delete account
        response = client.delete("/api/auth/account", headers=delete_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify user no longer exists
        deleted_user = db_session.query(User).filter_by(email="delete@example.com").first()
        assert deleted_user is None
    
    def test_request_password_reset(self, client: TestClient, test_user: User):
        """Test requesting password reset"""
        reset_data = {"email": test_user.email}
        
        response = client.post("/api/auth/forgot-password", json=reset_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        # Should not reveal whether email exists or not
        assert "if registered" in data["message"].lower()
    
    def test_request_password_reset_nonexistent(self, client: TestClient):
        """Test password reset for non-existent email"""
        reset_data = {"email": "nobody@example.com"}
        
        response = client.post("/api/auth/forgot-password", json=reset_data)
        
        # Should return same response as existing email (security)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "if registered" in data["message"].lower()
