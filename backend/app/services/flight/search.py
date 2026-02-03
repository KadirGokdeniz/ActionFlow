"""
Flight search service - Amadeus API entegrasyonu.
"""
from typing import Optional, Dict, Any, List
import logging

from app.services.integration.amadeus.client import amadeus_get

logger = logging.getLogger("ActionFlow-FlightSearch")


async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    return_date: Optional[str] = None,
    travel_class: Optional[str] = None,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Amadeus Flight Offers Search API'sini çağırır.

    ⚠️ Bu fonksiyon SADECE raw Amadeus flight-offer listesi döndürür.
    Normalize etmez.
    """

    params = {
        "originLocationCode": origin.upper(),
        "destinationLocationCode": destination.upper(),
        "departureDate": departure_date,
        "adults": adults,
        "max": max_results,
        "currencyCode": "EUR"
    }

    if return_date:
        params["returnDate"] = return_date

    if travel_class:
        params["travelClass"] = travel_class.upper()

    try:
        response = await amadeus_get("/v2/shopping/flight-offers", params)

        if not isinstance(response, dict):
            raise ValueError(f"Unexpected Amadeus response type: {type(response)}")

        flights = response.get("data")
        if not isinstance(flights, list):
            raise ValueError("Amadeus response.data is not a list")

        # 🔐 SADECE raw flight-offer'lar
        raw_flights: List[Dict[str, Any]] = [
            f for f in flights
            if isinstance(f, dict) and f.get("type") == "flight-offer"
        ]

        logger.info(
            f"✈️ Amadeus search OK | {origin}->{destination} | offers={len(raw_flights)}"
        )

        return {
            "flights": raw_flights,
            "raw": response
        }

    except Exception as e:
        logger.exception("❌ Amadeus flight search failed")
        return {
            "flights": [],
            "raw": None,
            "error": str(e)
        }
