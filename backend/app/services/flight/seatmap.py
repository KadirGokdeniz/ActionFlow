"""
Flight seatmap service - Amadeus API entegrasyonu.
"""
from typing import List, Dict, Any
from app.services.integration.amadeus.client import amadeus_post


async def get_seatmap(raw_offer: Any) -> List[Dict[str, Any]]:
    """
    Amadeus Seatmap Display API ile koltuk haritasını getirir.

    ⚠️ SADECE raw Amadeus flight-offer kabul eder.
    """

    # 🛑 GUARD: input doğrulama
    if not isinstance(raw_offer, dict):
        return []

    if raw_offer.get("type") != "flight-offer":
        return []

    request_body = {
        "data": [raw_offer]
    }

    try:
        response = await amadeus_post("/v1/shopping/seatmaps", request_body)

        if isinstance(response, dict):
            data = response.get("data")
            if isinstance(data, list):
                return data

        if isinstance(response, list):
            return response

        return []

    except Exception:
        return []


def parse_seatmap(raw_seatmap: Any) -> Dict[str, Any]:
    """
    Ham seatmap verisini kullanışlı formata dönüştürür.

    ⚠️ SADECE raw Amadeus seatmap dict parse edilir.
    """

    if not isinstance(raw_seatmap, dict):
        return {
            "aircraft": None,
            "available_seats": [],
            "total_available": 0
        }

    decks = raw_seatmap.get("decks")
    if not isinstance(decks, list):
        decks = []

    available_seats: List[Dict[str, Any]] = []

    for deck in decks:
        if not isinstance(deck, dict):
            continue

        seats = deck.get("seats")
        if not isinstance(seats, list):
            continue

        for seat in seats:
            if not isinstance(seat, dict):
                continue

            traveler_pricing = seat.get("travelerPricing")
            if not isinstance(traveler_pricing, list) or not traveler_pricing:
                continue

            pricing = traveler_pricing[0]
            if not isinstance(pricing, dict):
                continue

            price = pricing.get("price", {})

            available_seats.append({
                "number": seat.get("number"),
                "cabin": seat.get("cabin"),
                "characteristics": seat.get("characteristicsCodes", []),
                "price": price.get("total"),
                "currency": price.get("currency")
            })

    return {
        "aircraft": raw_seatmap.get("aircraft", {}).get("code"),
        "available_seats": available_seats,
        "total_available": len(available_seats)
    }
