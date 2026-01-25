"""Tests for authentication endpoints and services."""

from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    decode_token,
    get_password_hash,
    get_user_by_email,
    get_user_by_username,
    verify_password,
)


# Test database setup
@pytest.fixture
def test_db():
    """Create an in-memory test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(test_db):
    """Create a test client with database override."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db):
    """Create a test user in the database."""
    hashed_password = get_password_hash("testpassword123")
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_password,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


# =============================================================================
# Unit Tests: Password Hashing
# =============================================================================


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_get_password_hash_returns_string(self):
        """Test that get_password_hash returns a string."""
        hashed = get_password_hash("password123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_get_password_hash_returns_bcrypt_format(self):
        """Test that hash is in bcrypt format."""
        hashed = get_password_hash("password123")
        # bcrypt hashes start with $2b$ or $2a$
        assert hashed.startswith("$2")

    def test_get_password_hash_different_for_same_input(self):
        """Test that same password produces different hashes (due to salt)."""
        hash1 = get_password_hash("password123")
        hash2 = get_password_hash("password123")
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test verify_password returns True for correct password."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verify_password returns False for wrong password."""
        hashed = get_password_hash("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty_password(self):
        """Test verify_password with empty password."""
        hashed = get_password_hash("somepassword")
        assert verify_password("", hashed) is False

    def test_verify_password_unicode(self):
        """Test verify_password with unicode characters."""
        password = "p@ssw0rd!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


# =============================================================================
# Unit Tests: JWT Tokens
# =============================================================================


class TestJWTTokens:
    """Tests for JWT token functions."""

    def test_create_access_token_returns_string(self):
        """Test that create_access_token returns a string."""
        token = create_access_token(data={"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """Test create_access_token with custom expiry."""
        token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(hours=1),
        )
        assert isinstance(token, str)

    def test_decode_token_valid(self):
        """Test decode_token with valid token."""
        token = create_access_token(data={"sub": "testuser"})
        token_data = decode_token(token)
        assert token_data.username == "testuser"

    def test_decode_token_invalid(self):
        """Test decode_token with invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.here")
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    def test_decode_token_missing_subject(self):
        """Test decode_token with token missing subject."""
        # Create token without 'sub' claim
        token = create_access_token(data={"other": "data"})
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401


# =============================================================================
# Unit Tests: User Database Operations
# =============================================================================


class TestUserDatabaseOperations:
    """Tests for user database operations."""

    def test_get_user_by_username_exists(self, test_db, test_user):
        """Test get_user_by_username when user exists."""
        user = get_user_by_username(test_db, "testuser")
        assert user is not None
        assert user.username == "testuser"

    def test_get_user_by_username_not_exists(self, test_db):
        """Test get_user_by_username when user doesn't exist."""
        user = get_user_by_username(test_db, "nonexistent")
        assert user is None

    def test_get_user_by_email_exists(self, test_db, test_user):
        """Test get_user_by_email when user exists."""
        user = get_user_by_email(test_db, "test@example.com")
        assert user is not None
        assert user.email == "test@example.com"

    def test_get_user_by_email_not_exists(self, test_db):
        """Test get_user_by_email when user doesn't exist."""
        user = get_user_by_email(test_db, "nonexistent@example.com")
        assert user is None

    def test_authenticate_user_valid(self, test_db, test_user):
        """Test authenticate_user with valid credentials."""
        user = authenticate_user(test_db, "testuser", "testpassword123")
        assert user is not None
        assert user.username == "testuser"

    def test_authenticate_user_wrong_password(self, test_db, test_user):
        """Test authenticate_user with wrong password."""
        user = authenticate_user(test_db, "testuser", "wrongpassword")
        assert user is None

    def test_authenticate_user_nonexistent_user(self, test_db):
        """Test authenticate_user with non-existent user."""
        user = authenticate_user(test_db, "nonexistent", "password")
        assert user is None

    def test_create_user_success(self, test_db):
        """Test create_user successfully creates a user."""
        user_data = UserCreate(
            username="newuser",
            email="newuser@example.com",
            password="newpassword123",
        )
        user = create_user(test_db, user_data)
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.is_active is True
        # Password should be hashed, not plain text
        assert user.hashed_password != "newpassword123"

    def test_create_user_duplicate_username(self, test_db, test_user):
        """Test create_user with duplicate username."""
        user_data = UserCreate(
            username="testuser",  # Already exists
            email="different@example.com",
            password="password123",
        )
        with pytest.raises(HTTPException) as exc_info:
            create_user(test_db, user_data)
        assert exc_info.value.status_code == 400
        assert "Username already registered" in exc_info.value.detail

    def test_create_user_duplicate_email(self, test_db, test_user):
        """Test create_user with duplicate email."""
        user_data = UserCreate(
            username="differentuser",
            email="test@example.com",  # Already exists
            password="password123",
        )
        with pytest.raises(HTTPException) as exc_info:
            create_user(test_db, user_data)
        assert exc_info.value.status_code == 400
        assert "Email already registered" in exc_info.value.detail


# =============================================================================
# Integration Tests: Register Endpoint
# =============================================================================


class TestRegisterEndpoint:
    """Tests for POST /api/auth/register endpoint."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        # Password should not be returned
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, client, test_user):
        """Test registration with duplicate username."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",  # Already exists from test_user fixture
                "email": "different@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "differentuser",
                "email": "test@example.com",  # Already exists from test_user fixture
                "password": "password123",
            },
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """Test registration with invalid email format."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "not-an-email",
                "password": "password123",
            },
        )
        assert response.status_code == 422  # Validation error

    def test_register_missing_username(self, client):
        """Test registration with missing username."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 422

    def test_register_missing_email(self, client):
        """Test registration with missing email."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "password": "password123",
            },
        )
        assert response.status_code == 422

    def test_register_missing_password(self, client):
        """Test registration with missing password."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "test@example.com",
            },
        )
        assert response.status_code == 422


# =============================================================================
# Integration Tests: Login Endpoint
# =============================================================================


class TestLoginEndpoint:
    """Tests for POST /api/auth/login endpoint."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "nonexistent",
                "password": "password123",
            },
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_missing_username(self, client):
        """Test login with missing username."""
        response = client.post(
            "/api/auth/login",
            json={
                "password": "password123",
            },
        )
        assert response.status_code == 422

    def test_login_missing_password(self, client):
        """Test login with missing password."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
            },
        )
        assert response.status_code == 422

    def test_login_token_is_valid(self, client, test_user):
        """Test that login returns a valid, decodable token."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        token = response.json()["access_token"]

        # Verify the token can be decoded and contains correct username
        token_data = decode_token(token)
        assert token_data.username == "testuser"


# =============================================================================
# Integration Tests: Full Flow
# =============================================================================


class TestAuthFlow:
    """Tests for complete authentication flows."""

    def test_register_then_login(self, client):
        """Test registering a new user and then logging in."""
        # Register
        register_response = client.post(
            "/api/auth/register",
            json={
                "username": "flowuser",
                "email": "flowuser@example.com",
                "password": "flowpassword123",
            },
        )
        assert register_response.status_code == 201

        # Login with the same credentials
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "flowuser",
                "password": "flowpassword123",
            },
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()
