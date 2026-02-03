import pytest
from app.services.flight.pricing import price_flight_offer


@pytest.mark.asyncio
async def test_price_flight_offer(mocker):
    raw_offer = {
        "id": "OFFER123",
        "price": {
            "total": "150.00",
            "currency": "EUR"
        },
        "itineraries": [
            {"segments": []}
        ]
    }

    amadeus_response = {
        "flightOffers": [raw_offer]
    }

    mocker.patch(
        "app.services.flight.pricing.amadeus_post",
        return_value=amadeus_response
    )

    result = await price_flight_offer(raw_offer)

    assert result.offer_id == "OFFER123"
    assert result.price == 150.0
    assert result.currency == "EUR"
