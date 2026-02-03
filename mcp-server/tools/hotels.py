"""
ActionFlow MCP Tools - Hotel Search
Amadeus API üzerinden otel arama işlemleri
"""

from typing import Optional, List
import httpx


# ═══════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS (MCP Schema)
# ═══════════════════════════════════════════════════════════════════

SEARCH_HOTELS_DEFINITION = {
    "name": "search_hotels",
    "description": "Belirtilen şehirde otel arar. Şehir kodu IATA formatında olmalı (PAR=Paris, IST=İstanbul, AMS=Amsterdam, LON=Londra gibi).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "city_code": {
                "type": "string",
                "description": "IATA şehir kodu (örn: PAR, IST, LON, AMS)"
            },
            "radius": {
                "type": "integer",
                "description": "Arama yarıçapı km cinsinden (varsayılan: 5)",
                "default": 5
            }
        },
        "required": ["city_code"]
    }
}

GET_HOTEL_OFFERS_DEFINITION = {
    "name": "get_hotel_offers",
    "description": "Belirli oteller için fiyat ve müsaitlik bilgisi alır. Tarihler YYYY-MM-DD formatında olmalı.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "hotel_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Otel ID listesi (en fazla 20)"
            },
            "check_in": {
                "type": "string",
                "description": "Giriş tarihi (YYYY-MM-DD)"
            },
            "check_out": {
                "type": "string",
                "description": "Çıkış tarihi (YYYY-MM-DD)"
            },
            "adults": {
                "type": "integer",
                "description": "Yetişkin sayısı (varsayılan: 1)",
                "default": 1
            }
        },
        "required": ["hotel_ids", "check_in", "check_out"]
    }
}

# Export için liste
TOOL_DEFINITIONS = [SEARCH_HOTELS_DEFINITION, GET_HOTEL_OFFERS_DEFINITION]


# ═══════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════

async def search_hotels(
    city_code: str,
    radius: int = 5,
    http_client: httpx.AsyncClient = None
) -> dict:
    """
    Şehirde otel arar
    
    Args:
        city_code: IATA şehir kodu
        radius: Arama yarıçapı (km)
        http_client: HTTP client
    
    Returns:
        Otel listesi veya hata
    """
    if http_client is None:
        return {"success": False, "error": "HTTP client not provided"}
    
    try:
        response = await http_client.get(
            f"/api/v1/hotels/search/city/{city_code.upper()}",
            params={"radius": radius}
        )
        response.raise_for_status()
        data = response.json()
        
        hotels = data.get("hotels", [])[:10]
        
        formatted_hotels = []
        for h in hotels:
            hotel_info = {
                "id": h.get("hotelId"),
                "name": h.get("name"),
                "chain": h.get("chainCode"),
            }
            
            # Mesafe bilgisi
            distance = h.get("distance", {})
            if distance:
                hotel_info["distance_km"] = distance.get("value")
                hotel_info["distance_unit"] = distance.get("unit", "KM")
            
            # Konum
            geo = h.get("geoCode", {})
            if geo:
                hotel_info["latitude"] = geo.get("latitude")
                hotel_info["longitude"] = geo.get("longitude")
            
            formatted_hotels.append(hotel_info)
        
        return {
            "success": True,
            "city": city_code.upper(),
            "radius_km": radius,
            "count": data.get("count", len(formatted_hotels)),
            "hotels": formatted_hotels
        }
        
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"API error: {e.response.status_code}",
            "detail": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def get_hotel_offers(
    hotel_ids: List[str],
    check_in: str,
    check_out: str,
    adults: int = 1,
    http_client: httpx.AsyncClient = None
) -> dict:
    """
    Otel fiyat ve müsaitlik bilgisi alır
    
    Args:
        hotel_ids: Otel ID listesi
        check_in: Giriş tarihi
        check_out: Çıkış tarihi
        adults: Yetişkin sayısı
        http_client: HTTP client
    
    Returns:
        Otel teklifleri veya hata
    """
    if http_client is None:
        return {"success": False, "error": "HTTP client not provided"}
    
    try:
        response = await http_client.post(
            "/api/v1/hotels/offers",
            json={
                "hotel_ids": hotel_ids[:20],  # Max 20 otel
                "check_in": check_in,
                "check_out": check_out,
                "adults": adults,
                "rooms": 1,
                "currency": "EUR"
            }
        )
        response.raise_for_status()
        data = response.json()
        
        offers = data.get("offers", [])
        
        formatted_offers = []
        for o in offers:
            hotel = o.get("hotel", {})
            offer_list = o.get("offers", [])
            
            if not offer_list:
                continue
            
            best_offer = offer_list[0]  # İlk (genelde en ucuz) teklif
            price = best_offer.get("price", {})
            
            offer_info = {
                "hotel_id": hotel.get("hotelId"),
                "hotel_name": hotel.get("name"),
                "price": price.get("total"),
                "currency": price.get("currency", "EUR"),
                "room_type": best_offer.get("room", {}).get("type"),
                "board_type": best_offer.get("boardType"),
                "cancellation": best_offer.get("policies", {}).get("cancellation", {}).get("description"),
            }
            
            formatted_offers.append(offer_info)
        
        # Fiyata göre sırala
        formatted_offers.sort(key=lambda x: float(x.get("price") or 999999))
        
        return {
            "success": True,
            "check_in": check_in,
            "check_out": check_out,
            "adults": adults,
            "count": len(formatted_offers),
            "cheapest": formatted_offers[0] if formatted_offers else None,
            "offers": formatted_offers
        }
        
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"API error: {e.response.status_code}",
            "detail": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }