"""
Integration tests for JWT authentication flow.
Tests register, login, and protected endpoint access.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.main import app
from app.core.database import get_db

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def db_override():
    """Mock DB that simulates empty user table."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    yield mock_db
    app.dependency_overrides.clear()


async def test_register_success(async_client, db_override):
    """POST /auth/register with valid data returns 201."""
    response = await async_client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword123",
        "first_name": "Test",
        "last_name": "User"
    })
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["email"] == "test@example.com"


async def test_register_duplicate_email(async_client, db_override):
    """POST /auth/register with existing email returns 400."""
    from unittest.mock import MagicMock
    existing_user = MagicMock()
    existing_user.email = "existing@example.com"
    db_override.execute.return_value.scalar_one_or_none.return_value = existing_user

    response = await async_client.post("/api/v1/auth/register", json={
        "email": "existing@example.com",
        "password": "password123",
        "first_name": "Dupe",
        "last_name": "User"
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


async def test_login_invalid_credentials(async_client, db_override):
    """POST /auth/login with wrong password returns 401."""
    response = await async_client.post("/api/v1/auth/login", data={
        "username": "nobody@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


async def test_login_success_returns_token(async_client, db_override):
    """POST /auth/login with correct credentials returns JWT token."""
    from app.core.auth import hash_password
    from unittest.mock import MagicMock

    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.email = "test@example.com"
    mock_user.password_hash = hash_password("correctpassword")
    db_override.execute.return_value.scalar_one_or_none.return_value = mock_user

    response = await async_client.post("/api/v1/auth/login", data={
        "username": "test@example.com",
        "password": "correctpassword"
    })
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


async def test_booking_without_token_returns_401(async_client):
    """POST /bookings/flight without Authorization header returns 401."""
    response = await async_client.post("/api/v1/bookings/flight", json={
        "passenger_name": "Test User",
        "email": "test@example.com",
        "offer_id": "OFFER_123"
    })
    assert response.status_code == 401


async def test_booking_with_invalid_token_returns_401(async_client):
    """POST /bookings/flight with invalid token returns 401."""
    response = await async_client.post(
        "/api/v1/bookings/flight",
        json={"offer_id": "OFFER_123"},
        headers={"Authorization": "Bearer this.is.not.a.valid.token"}
    )
    assert response.status_code == 401
