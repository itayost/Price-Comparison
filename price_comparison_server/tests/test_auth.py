# tests/test_auth.py
import pytest
from fastapi import status

def test_user_registration(client):
    """Test that users can register successfully"""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "testpass123"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "user_id" in data

def test_duplicate_registration(client):
    """Test that duplicate emails are rejected"""
    # First registration
    client.post(
        "/api/auth/register",
        json={"email": "duplicate@example.com", "password": "testpass123"}
    )
    
    # Try to register again with same email
    response = client.post(
        "/api/auth/register",
        json={"email": "duplicate@example.com", "password": "different123"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_login_success(client):
    """Test successful login returns JWT token"""
    # Register first
    client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "testpass123"}
    )
    
    # Now login
    response = client.post(
        "/api/auth/login",
        data={"username": "login@example.com", "password": "testpass123"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client):
    """Test login with wrong password fails"""
    # Register first
    client.post(
        "/api/auth/register",
        json={"email": "wrong@example.com", "password": "correctpass"}
    )
    
    # Try to login with wrong password
    response = client.post(
        "/api/auth/login",
        data={"username": "wrong@example.com", "password": "wrongpass"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
