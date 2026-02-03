from typing import Any
from app.services.integration.amadeus.client import amadeus_post
from app.models.flight_models import PricingResponse


async def price_flight_offer(offer_data: Any) -> PricingResponse:
    """
    Amadeus flight-offers/pricing API'sini çağırır.

    ⚠️ Bu fonksiyon SADECE raw Amadeus pricing payload kabul eder.
    """

    # 🛑 GUARD: input doğrulama
    if not isinstance(offer_data, dict):
        return PricingResponse(
            offer_id="invalid",
            total="0.00",
            currency="EUR"
        )

    response = await amadeus_post(
        "/v1/shopping/flight-offers/pricing",
        body=offer_data
    )

    # 🛑 GUARD: response doğrulama
    if not isinstance(response, dict):
        return PricingResponse(
            offer_id="invalid",
            total="0.00",
            currency="EUR"
        )

    flight_offers = response.get("flightOffers")
    if not isinstance(flight_offers, list) or not flight_offers:
        return PricingResponse(
            offer_id="invalid",
            total="0.00",
            currency="EUR"
        )

    offer = flight_offers[0]
    if not isinstance(offer, dict):
        return PricingResponse(
            offer_id="invalid",
            total="0.00",
            currency="EUR"
        )

    price_data = offer.get("price")
    if not isinstance(price_data, dict):
        return PricingResponse(
            offer_id=offer.get("id", "unknown"),
            total="0.00",
            currency="EUR"
        )

    return PricingResponse(
        offer_id=offer.get("id", "unknown"),
        total=price_data.get("total", "0.00"),
        currency=price_data.get("currency", "EUR")
    )
