"""
Flight booking service - Amadeus API entegrasyonu.
"""
from typing import List, Optional, Any
from app.services.integration.amadeus.client import amadeus_post
from app.models.flight_models import (
    BookingResult,
    Passenger,
    Contact,
    SelectedSeat,
    SelectedBaggage
)


async def create_flight_order(
    raw_offer: Any,
    passenger: Passenger,
    contact: Contact,
    seats: Optional[List[SelectedSeat]] = None,
    baggage: Optional[SelectedBaggage] = None
) -> BookingResult:
    """
    Amadeus Flight Orders API ile rezervasyon oluşturur.

    ⚠️ Bu fonksiyon SADECE raw Amadeus flight-offer kabul eder.
    Yanlış input gelirse fail-fast davranır.
    """

    # 🛑 GUARD: raw_offer doğrulaması
    if not isinstance(raw_offer, dict):
        return BookingResult(
            order_id="",
            status="FAILED",
            ticketed=False,
            total_price=0,
            currency="EUR",
            warnings=["Invalid flight offer format (not a dict)"]
        )

    if raw_offer.get("type") != "flight-offer":
        return BookingResult(
            order_id="",
            status="FAILED",
            ticketed=False,
            total_price=0,
            currency="EUR",
            warnings=["Invalid flight offer schema (not raw Amadeus flight-offer)"]
        )

    # Traveler verisi
    traveler = {
        "id": passenger.id,
        "dateOfBirth": passenger.date_of_birth,
        "name": {
            "firstName": passenger.first_name,
            "lastName": passenger.last_name
        },
        "gender": passenger.gender,
        "contact": {
            "emailAddress": contact.email,
            "phones": [{
                "deviceType": "MOBILE",
                "countryCallingCode": "90",
                "number": contact.phone
            }]
        }
    }

    booking_data = {
        "data": {
            "type": "flight-order",
            "flightOffers": [raw_offer],
            "travelers": [traveler],
            "remarks": {
                "general": [{
                    "subType": "GENERAL_MISCELLANEOUS",
                    "text": "ActionFlow AI Booking"
                }]
            }
        }
    }

    try:
        response = await amadeus_post("/v1/booking/flight-orders", booking_data)

        if not isinstance(response, dict):
            raise ValueError("Invalid Amadeus booking response")

        # PNR
        pnr = None
        records = response.get("associatedRecords")
        if isinstance(records, list) and records:
            pnr = records[0].get("reference")

        # Fiyat bilgisi
        flight_offers = response.get("flightOffers")
        price_data = {}
        if isinstance(flight_offers, list) and flight_offers:
            price_data = flight_offers[0].get("price", {})

        return BookingResult(
            order_id=response.get("id", "") or "",
            status="CONFIRMED" if response.get("id") else "FAILED",
            ticketed=False,
            total_price=float(price_data.get("total", 0) or 0),
            currency=price_data.get("currency", "EUR"),
            warnings=[
                w.get("detail", "")
                for w in response.get("warnings", [])
                if isinstance(w, dict)
            ]
        )

    except Exception as e:
        return BookingResult(
            order_id="",
            status="FAILED",
            ticketed=False,
            total_price=0,
            currency="EUR",
            warnings=[str(e)]
        )
