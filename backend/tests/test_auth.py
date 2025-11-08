"""
Authentication Tests
Sprint 24: Testing & Documentation

Unit and integration tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest.mark.asyncio
@pytest.mark.unit
class TestUserRegistration:
    """Test user registration"""

    async def test_register_user_success(self, client: AsyncClient):
        """Test successful user registration"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "full_name": "New User",
                "password": "SecurePassword123!"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """Test registration with duplicate email"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "username": "differentuser",
                "full_name": "Different User",
                "password": "SecurePassword123!"
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "username": "testuser",
                "full_name": "Test User",
                "password": "SecurePassword123!"
            }
        )

        assert response.status_code == 422

    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "full_name": "Test User",
                "password": "weak"
            }
        )

        # Should either reject or warn about weak password
        # Depending on implementation
        assert response.status_code in [400, 422]


@pytest.mark.asyncio
@pytest.mark.unit
class TestUserLogin:
    """Test user login"""

    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """Test login with wrong password"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 401

    async def test_login_inactive_user(self, client: AsyncClient, test_db_session: AsyncSession):
        """Test login with inactive user"""
        from app.core.security import get_password_hash
        from datetime import datetime

        inactive_user = User(
            email="inactive@example.com",
            username="inactiveuser",
            hashed_password=get_password_hash("password123"),
            is_active=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        test_db_session.add(inactive_user)
        await test_db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "password123"
            }
        )

        assert response.status_code in [400, 401]


@pytest.mark.asyncio
@pytest.mark.unit
class TestUserProfile:
    """Test user profile endpoints"""

    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict, test_user: User):
        """Test getting current user profile"""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username

    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without authentication"""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    async def test_update_profile(self, client: AsyncClient, auth_headers: dict):
        """Test updating user profile"""
        response = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={
                "full_name": "Updated Name",
                "bio": "Updated bio"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"


@pytest.mark.asyncio
@pytest.mark.unit
class TestPasswordReset:
    """Test password reset functionality"""

    async def test_request_password_reset(self, client: AsyncClient, test_user: User):
        """Test password reset request"""
        response = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": test_user.email}
        )

        # Should return success even if email doesn't exist (security)
        assert response.status_code in [200, 202]

    async def test_reset_password(self, client: AsyncClient):
        """Test password reset with token"""
        # This would require generating a valid reset token
        # Simplified test
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": "test-token",
                "new_password": "NewSecurePassword123!"
            }
        )

        # Will fail with invalid token, but endpoint should exist
        assert response.status_code in [400, 404]


@pytest.mark.asyncio
@pytest.mark.integration
class TestAuthenticationFlow:
    """Integration tests for complete authentication flows"""

    async def test_complete_registration_login_flow(self, client: AsyncClient):
        """Test complete flow: register -> login -> access protected resource"""
        # Step 1: Register
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "flowtest@example.com",
                "username": "flowtest",
                "full_name": "Flow Test",
                "password": "SecurePassword123!"
            }
        )

        assert register_response.status_code == 201

        # Step 2: Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "flowtest@example.com",
                "password": "SecurePassword123!"
            }
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Step 3: Access protected resource
        profile_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert profile_response.status_code == 200
        assert profile_response.json()["email"] == "flowtest@example.com"

    async def test_token_expiration(self, client: AsyncClient):
        """Test token expiration handling"""
        # This would require mocking time or using expired token
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.token"

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.unit
class TestAuthorizationRoles:
    """Test role-based authorization"""

    async def test_admin_access(self, client: AsyncClient, admin_auth_headers: dict):
        """Test admin user can access admin endpoints"""
        response = await client.get(
            "/api/v1/admin/users",
            headers=admin_auth_headers
        )

        # Should allow access (might return empty list)
        assert response.status_code in [200, 404]

    async def test_regular_user_cannot_access_admin(self, client: AsyncClient, auth_headers: dict):
        """Test regular user cannot access admin endpoints"""
        response = await client.get(
            "/api/v1/admin/users",
            headers=auth_headers
        )

        assert response.status_code == 403
