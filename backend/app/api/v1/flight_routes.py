"""
ActionFlow API - Flight Routes
Amadeus API üzerinden uçuş işlemleri

Endpoints:
    GET  /flights/search           - Uçuş arama
    POST /flights/price/{id}       - Fiyat sorgulama
    POST /flights/book/{id}        - Rezervasyon
    GET  /flights/{id}/seatmap     - Koltuk haritası
    GET  /flights/{id}/ancillaries - Ek hizmetler
"""

from typing import List, Optional
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder

from app.services.flight.offer_cache import get_offer, cache_offers
from app.services.flight.search import search_flights
from app.services.flight.pricing import price_flight_offer
from app.services.flight.booking import create_flight_order
from app.services.flight.seatmap import get_seatmap
from app.services.flight.ancillary_mapper import map_baggage_ancillaries
from app.models.flight_models import (
    Passenger, Contact, SelectedSeat, SelectedBaggage
)

router = APIRouter(prefix="/flights", tags=["Flights"])
logger = logging.getLogger("ActionFlow-Flights")


# --------------------------------------------------
# FLIGHT SEARCH (MCP Server bu endpoint'i çağırır)
# --------------------------------------------------
@router.get("/search")
async def search_flights_endpoint(
    origin: str = Query(..., min_length=3, max_length=3, description="Kalkış IATA kodu"),
    destination: str = Query(..., min_length=3, max_length=3, description="Varış IATA kodu"),
    date: str = Query(..., description="Uçuş tarihi (YYYY-MM-DD)"),
    adults: int = Query(default=1, ge=1, le=9, description="Yolcu sayısı"),
    return_date: Optional[str] = Query(default=None, description="Dönüş tarihi (opsiyonel)"),
    max_results: int = Query(default=10, ge=1, le=50, description="Maksimum sonuç sayısı")
):
    """
    Uçuş arama endpoint'i
    """
    try:
        results = await search_flights(
            origin=origin.upper(),
            destination=destination.upper(),
            departure_date=date,
            adults=adults,
            return_date=return_date,
            max_results=max_results
        )

        if not isinstance(results, dict):
            raise ValueError("search_flights did not return a dict")

        flights = results.get("flights") or []

        logger.info(
            f"✈️ Flight search OK | {origin.upper()} → {destination.upper()} | count={len(flights)}"
        )

        # Offer cache (price / book için)
        if flights:
            cache_offers(flights)

        # En ucuz uçuş
        cheapest = None
        if flights:
            prices = []
            for f in flights:
                try:
                    prices.append(float(f["price"]["total"]))
                except Exception:
                    prices.append(999999)

            min_price = min(prices)
            cheapest_flight = flights[prices.index(min_price)]
            cheapest = (
                f"{cheapest_flight['price']['total']} "
                f"{cheapest_flight['price'].get('currency', 'EUR')}"
            )

        response = {
            "success": True,
            "route": f"{origin.upper()} → {destination.upper()}",
            "date": date,
            "return_date": return_date,
            "count": len(flights),
            "cheapest": cheapest,
            "flights": flights[:max_results]
        }

        # JSON-safe dönüş (Decimal / datetime vs. için)
        return jsonable_encoder(response)

    except Exception as e:
        logger.exception("❌ Flight search endpoint crashed")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# FLIGHT PRICING
# --------------------------------------------------
@router.post("/price/{offer_id}")
async def price_flight(offer_id: str):
    """
    Uçuş fiyatını doğrula ve detayları al
    """
    raw_offer = get_offer(offer_id)
    if not raw_offer:
        raise HTTPException(410, "Flight offer expired. Please search again.")

    try:
        result = await price_flight_offer(raw_offer)
        return jsonable_encoder(result)
    except Exception as e:
        logger.exception("❌ Flight pricing failed")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# FLIGHT BOOKING
# --------------------------------------------------
@router.post("/book/{offer_id}")
async def book_flight(
    offer_id: str,
    passenger: Passenger,
    contact: Contact,
    seats: Optional[List[SelectedSeat]] = None,
    baggage: Optional[SelectedBaggage] = None
):
    """
    Uçuş rezervasyonu oluştur
    """
    raw_offer = get_offer(offer_id)
    if not raw_offer:
        raise HTTPException(410, "Flight offer expired. Please search again.")

    try:
        result = await create_flight_order(
            raw_offer=raw_offer,
            passenger=passenger,
            contact=contact,
            seats=seats,
            baggage=baggage
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.exception("❌ Flight booking failed")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# SEATMAP
# --------------------------------------------------
@router.get("/{offer_id}/seatmap")
async def seatmap(offer_id: str):
    """
    Uçuş için koltuk haritası
    """
    raw_offer = get_offer(offer_id)
    if not raw_offer:
        raise HTTPException(410, "Flight offer expired")

    try:
        result = await get_seatmap(raw_offer)
        return jsonable_encoder(result)
    except Exception as e:
        logger.exception("❌ Seatmap retrieval failed")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# ANCILLARIES (Baggage, etc.)
# --------------------------------------------------
@router.get("/{offer_id}/ancillaries")
async def ancillaries(offer_id: str):
    """
    Ek hizmetler (bagaj, yemek vb.)
    """
    raw_offer = get_offer(offer_id)
    if not raw_offer:
        raise HTTPException(410, "Flight offer expired")

    try:
        result = map_baggage_ancillaries(raw_offer)
        return jsonable_encoder(result)
    except Exception as e:
        logger.exception("❌ Ancillary mapping failed")
        raise HTTPException(status_code=500, detail=str(e))
