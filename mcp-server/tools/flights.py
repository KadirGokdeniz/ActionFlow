"""
ActionFlow MCP Tools - Flight Search
Amadeus API üzerinden uçuş arama işlemleri
"""

from typing import Optional
import httpx

# Backend URL (server.py'den alınacak)
BACKEND_URL = None


def set_backend_url(url: str):
    """Backend URL'i ayarla (server.py tarafından çağrılır)"""
    global BACKEND_URL
    BACKEND_URL = url


# ═══════════════════════════════════════════════════════════════════
# TOOL DEFINITION (MCP Schema)
# ═══════════════════════════════════════════════════════════════════

TOOL_DEFINITION = {
    "name": "search_flights",
    "description": "İki şehir arasında uçuş arar. Şehir kodları IATA formatında olmalı (IST=İstanbul, JFK=New York, LHR=Londra, CDG=Paris gibi).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "origin": {
                "type": "string",
                "description": "Kalkış şehri IATA kodu (örn: IST)"
            },
            "destination": {
                "type": "string",
                "description": "Varış şehri IATA kodu (örn: PAR)"
            },
            "date": {
                "type": "string",
                "description": "Uçuş tarihi (YYYY-MM-DD formatında)"
            },
            "adults": {
                "type": "integer",
                "description": "Yolcu sayısı (varsayılan: 1)",
                "default": 1
            },
            "return_date": {
                "type": "string",
                "description": "Dönüş tarihi (opsiyonel, gidiş-dönüş için YYYY-MM-DD)"
            }
        },
        "required": ["origin", "destination", "date"]
    }
}


# ═══════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════

async def search_flights(
    origin: str,
    destination: str,
    date: str,
    adults: int = 1,
    return_date: Optional[str] = None,
    http_client: httpx.AsyncClient = None
) -> dict:
    """
    Uçuş arar
    
    Args:
        origin: Kalkış IATA kodu
        destination: Varış IATA kodu
        date: Uçuş tarihi (YYYY-MM-DD)
        adults: Yolcu sayısı
        return_date: Dönüş tarihi (opsiyonel)
        http_client: HTTP client (dependency injection)
    
    Returns:
        Uçuş sonuçları veya hata
    """
    if http_client is None:
        return {"success": False, "error": "HTTP client not provided"}
    
    try:
        params = {
            "origin": origin.upper(),
            "destination": destination.upper(),
            "date": date,
            "adults": adults,
            "max_results": 5
        }
        
        if return_date:
            params["return_date"] = return_date
        
        response = await http_client.get("/api/v1/flights/search", params=params)
        response.raise_for_status()
        data = response.json()
        
        flights = data.get("flights", [])
        
        # Sonuçları formatla
        formatted_flights = []
        for f in flights[:5]:
            price = f.get("price", {})
            segments = f.get("segments", [])
            
            flight_info = {
                "price": price.get("total"),
                "currency": price.get("currency", "EUR"),
                "duration": f.get("duration"),
                "stops": len(segments) - 1 if segments else 0,
            }
            
            # İlk segment bilgisi
            if segments:
                first_seg = segments[0]
                flight_info["carrier"] = first_seg.get("carrierCode")
                flight_info["flight_number"] = first_seg.get("number")
                flight_info["departure_time"] = first_seg.get("departure", {}).get("at")
                flight_info["arrival_time"] = segments[-1].get("arrival", {}).get("at")
            
            formatted_flights.append(flight_info)
        
        return {
            "success": True,
            "route": f"{origin.upper()} → {destination.upper()}",
            "date": date,
            "return_date": return_date,
            "count": data.get("count", len(formatted_flights)),
            "cheapest": data.get("cheapest"),
            "flights": formatted_flights
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