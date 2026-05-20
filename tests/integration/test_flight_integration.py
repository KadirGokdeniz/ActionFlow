"""
Integration tests for /api/v1/flights endpoints.
External Amadeus API calls are mocked to avoid network requests.
"""
import pytest
from unittest.mock import AsyncMock

pytestmark = pytest.mark.asyncio


async def test_flight_search_missing_required_params(async_client):
    """
    GET /flights/search without required params (origin, destination, date)
    should return 422 ? FastAPI validates before reaching service code.
    """
    response = await async_client.get("/api/v1/flights/search")
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


async def test_flight_search_invalid_iata_length(async_client):
    """IATA codes must be exactly 3 characters (min_length=3, max_length=3)."""
    response = await async_client.get(
        "/api/v1/flights/search",
        params={"origin": "IS", "destination": "AMSTERDAM", "date": "2026-06-01"}
    )
    assert response.status_code == 422


async def test_flight_search_with_mocked_amadeus(async_client, mocker):
    """
    Full flight search flow with mocked Amadeus.
    Verifies the endpoint calls search_flights and returns formatted results.
    """
    mock_response = {
        "data": [
            {
                "id": "OFFER_TEST_1",
                "price": {"total": "199.99", "currency": "EUR"},
                "itineraries": [
                    {
                        "segments": [
                            {
                                "departure": {"iataCode": "IST", "at": "2026-06-01T08:00:00"},
                                "arrival":   {"iataCode": "AMS", "at": "2026-06-01T10:30:00"},
                                "carrierCode": "TK",
                                "number": "1951",
                                "numberOfStops": 0,
                            }
                        ],
                        "duration": "PT2H30M",
                    }
                ],
                "travelerPricings": [],
                "validatingAirlineCodes": ["TK"],
                "lastTicketingDate": "2026-05-25",
            }
        ],
        "meta": {"count": 1}
    }

    mocker.patch(
        "app.api.v1.flight_routes.search_flights",
        new_callable=AsyncMock,
        return_value=mock_response
    )

    response = await async_client.get(
        "/api/v1/flights/search",
        params={
            "origin": "IST",
            "destination": "AMS",
            "date": "2026-06-01",
            "adults": 1,
        }
    )
    assert response.status_code == 200
    body = response.json()
    # Response format: {"flights": [...], "count": N, "date": "...", "cheapest": ...}
    assert isinstance(body, dict)
    assert "flights" in body
    assert "count" in body
    assert body["date"] == "2026-06-01"
