"""
ActionFlow API - Hotel/Accommodation Routes
Booking.com ve Amadeus API üzerinden otel işlemleri

Endpoints:
    GET  /hotels/search/city/{code}  - Şehirde otel arama
    POST /hotels/offers              - Otel fiyat/müsaitlik
    GET  /hotels/search-destination  - Destinasyon arama (Booking.com)
    GET  /hotels/{id}/policies       - Otel politikaları
    GET  /hotels/{id}/description    - Otel açıklaması
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from app.services.integration.booking.client import booking_get
from app.services.accommodation.hotel_models import HotelOffer

router = APIRouter(prefix="/hotels", tags=["Hotels"])


# --------------------------------------------------
# REQUEST/RESPONSE MODELS
# --------------------------------------------------

class HotelOffersRequest(BaseModel):
    hotel_ids: List[str]
    check_in: str
    check_out: str
    adults: int = 1
    rooms: int = 1
    currency: str = "EUR"


# --------------------------------------------------
# HOTEL SEARCH BY CITY (MCP Server bu endpoint'i çağırır)
# --------------------------------------------------
@router.get("/search/city/{city_code}")
async def search_hotels_by_city(
    city_code: str,
    radius: int = Query(default=5, ge=1, le=50, description="Arama yarıçapı (km)")
):
    """
    Şehir koduna göre otel arama
    
    - city_code: IATA şehir kodu (örn: PAR, IST, AMS)
    - radius: Şehir merkezinden yarıçap (km)
    """
    try:
        # Amadeus Hotel List API çağrısı
        from app.services.integration.amadeus.client import search_hotels_by_city_logic
        
        result = await search_hotels_by_city_logic(
            city_code=city_code.upper(),
            radius=radius
        )
        
        return {
            "success": True,
            "city": city_code.upper(),
            "radius_km": radius,
            "count": result.get("count", 0),
            "hotels": result.get("hotels", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# HOTEL OFFERS (Fiyat ve Müsaitlik)
# --------------------------------------------------
@router.post("/offers")
async def get_hotel_offers(request: HotelOffersRequest):
    """
    Belirli oteller için fiyat ve müsaitlik bilgisi
    
    - hotel_ids: Otel ID listesi (max 20)
    - check_in: Giriş tarihi (YYYY-MM-DD)
    - check_out: Çıkış tarihi (YYYY-MM-DD)
    - adults: Yetişkin sayısı
    """
    try:
        from app.services.integration.amadeus.client import get_hotel_offers_logic
        
        result = await get_hotel_offers_logic(
            hotel_ids=request.hotel_ids[:20],
            check_in=request.check_in,
            check_out=request.check_out,
            adults=request.adults,
            rooms=request.rooms,
            currency=request.currency
        )
        
        return {
            "success": True,
            "check_in": request.check_in,
            "check_out": request.check_out,
            "offers": result.get("offers", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# BOOKING.COM DESTINATION SEARCH
# --------------------------------------------------
@router.get("/search-destination")
def booking_search_destination(
    city: str | None = None,
    city_name: str | None = None,
    locale: str = "en-gb"
):
    """
    Booking.com destinasyon arama
    """
    city_value = city or city_name
    if not city_value:
        raise HTTPException(status_code=422, detail="city or city_name required")

    return booking_get(
        "/v1/hotels/locations",
        {
            "name": city_value,
            "locale": locale
        }
    )


# --------------------------------------------------
# HOTEL SEARCH (Legacy - Booking.com)
# --------------------------------------------------
@router.get("/search", response_model=List[HotelOffer])
async def search(
    dest_id: str,
    arrival_date: str,
    departure_date: str,
    adults: int = 1
):
    """
    Booking.com otel arama (placeholder)
    """
    # TODO: Booking.com availability API entegrasyonu
    return []


# --------------------------------------------------
# HOTEL POLICIES
# --------------------------------------------------
@router.get("/{hotel_id}/policies")
def booking_hotel_policies(hotel_id: str):
    """
    Otel politikaları (iptal, check-in vb.)
    """
    # TODO: Gerçek API entegrasyonu
    return {
        "hotel_id": hotel_id,
        "policies": [
            "Free cancellation available",
            "No smoking rooms",
            "Pets allowed on request"
        ],
        "source": "mock"
    }


# --------------------------------------------------
# HOTEL DESCRIPTION
# --------------------------------------------------
@router.get("/{hotel_id}/description")
def booking_hotel_description(hotel_id: str):
    """
    Otel açıklaması ve detayları
    """
    # TODO: Gerçek API entegrasyonu
    return {
        "hotel_id": hotel_id,
        "description": (
            "This hotel offers comfortable rooms, free WiFi, "
            "24-hour reception and a central location."
        ),
        "source": "mock"
    }