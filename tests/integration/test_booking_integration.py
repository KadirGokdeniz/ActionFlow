"""
Integration tests for booking flow.
Tests create_flight_booking (happy + failure) and cancel_booking (happy + failure).
JWT auth is bypassed via dependency override.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio

VALID_FLIGHT_REQUEST = {
    "offer_id": "OFFER_TEST_123",
    "passengers": [
        {
            "first_name": "Ahmet",
            "last_name": "Yilmaz",
            "email": "ahmet@example.com",
            "phone": "+905551234567"
        }
    ],
    "contact_email": "ahmet@example.com",
    "contact_phone": "+905551234567"
}


@pytest.fixture(autouse=True)
def override_auth():
    """Bypass JWT auth for all tests in this file."""
    from app.main import app
    from app.core.auth import get_current_user

    mock_user = MagicMock()
    mock_user.id = "test-user-123"
    mock_user.email = "test@example.com"

    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


# ?? CREATE FLIGHT BOOKING ????????????????????????????????????????????????????

async def test_create_flight_booking_returns_confirmed(async_client, mocker):
    """Happy path: valid request returns 200 with confirmed booking."""
    mocker.patch(
        "app.api.v1.booking_routes.trigger_booking_confirmation",
        new_callable=AsyncMock
    )
    response = await async_client.post("/api/v1/bookings/flight", json=VALID_FLIGHT_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["status"] == "confirmed"
    assert body["booking_type"] == "flight"
    assert "booking_id" in body and len(body["booking_id"]) > 0
    assert "pnr" in body and len(body["pnr"]) > 0
    assert body["total_amount"] > 0


async def test_create_flight_booking_missing_offer_id(async_client):
    """Failure: missing offer_id returns 422 Unprocessable Entity."""
    response = await async_client.post("/api/v1/bookings/flight", json={
        "passengers": [{"first_name": "A", "last_name": "B", "email": "a@b.com"}],
        "contact_email": "a@b.com"
    })
    assert response.status_code == 422
    assert "detail" in response.json()


async def test_create_flight_booking_invalid_email(async_client):
    """Failure: invalid email format returns 422."""
    response = await async_client.post("/api/v1/bookings/flight", json={
        "offer_id": "OFFER_123",
        "passengers": [{"first_name": "A", "last_name": "B", "email": "not-an-email"}],
        "contact_email": "also-invalid"
    })
    assert response.status_code == 422


async def test_create_flight_booking_without_auth(async_client):
    """Failure: no auth token returns 401."""
    from app.main import app
    from app.core.auth import get_current_user
    app.dependency_overrides.pop(get_current_user, None)  # remove override for this test

    response = await async_client.post("/api/v1/bookings/flight", json=VALID_FLIGHT_REQUEST)
    assert response.status_code == 401

    # Restore override for other tests
    mock_user = MagicMock()
    mock_user.id = "test-user-123"
    app.dependency_overrides[get_current_user] = lambda: mock_user


# ?? CANCEL BOOKING ????????????????????????????????????????????????????????????

async def test_cancel_booking_happy_path(async_client, mocker):
    """Happy path: create then cancel a booking."""
    mocker.patch("app.api.v1.booking_routes.trigger_booking_confirmation", new_callable=AsyncMock)
    mocker.patch("app.api.v1.booking_routes.trigger_cancellation_notification", new_callable=AsyncMock)

    # Create booking
    create_resp = await async_client.post("/api/v1/bookings/flight", json=VALID_FLIGHT_REQUEST)
    assert create_resp.status_code == 200
    booking_id = create_resp.json()["booking_id"]

    # Cancel it
    cancel_resp = await async_client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        json={"reason": "Changed plans"}
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


async def test_cancel_booking_not_found(async_client):
    """Failure: cancel non-existent booking returns 404."""
    response = await async_client.post(
        "/api/v1/bookings/nonexistent-booking-xyz/cancel",
        json={"reason": "test"}
    )
    assert response.status_code == 404
