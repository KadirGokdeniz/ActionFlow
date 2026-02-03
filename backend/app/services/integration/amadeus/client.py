"""
Amadeus API Client
ActionFlow AI - Real API Integration

Handles OAuth2 authentication and API calls to Amadeus Self-Service APIs.
"""

import os
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

load_dotenv()

# Logging
logger = logging.getLogger("AmadeusClient")

# Configuration
API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")
HOSTNAME = os.getenv("AMADEUS_HOSTNAME", "test.api.amadeus.com")
BASE_URL = f"https://{HOSTNAME}"

# Token cache
_token_cache = {
    "access_token": None,
    "expires_at": None
}


async def get_access_token() -> str:
    """
    Get OAuth2 access token from Amadeus.
    Caches token until expiry.
    """
    global _token_cache
    
    # Check if we have a valid cached token
    if _token_cache["access_token"] and _token_cache["expires_at"]:
        if datetime.now() < _token_cache["expires_at"]:
            return _token_cache["access_token"]
    
    # Request new token
    if not API_KEY or not API_SECRET:
        raise ValueError("AMADEUS_API_KEY and AMADEUS_API_SECRET must be set in .env")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": API_KEY,
                "client_secret": API_SECRET
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            logger.error(f"Token request failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to get Amadeus token: {response.status_code}")
        
        data = response.json()
        _token_cache["access_token"] = data["access_token"]
        # Token expires in 'expires_in' seconds, subtract 60 for safety margin
        expires_in = data.get("expires_in", 1799) - 60
        _token_cache["expires_at"] = datetime.now() + timedelta(seconds=expires_in)
        
        logger.info("✅ Amadeus token refreshed")
        return _token_cache["access_token"]


async def amadeus_get(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Make GET request to Amadeus API.
    ALWAYS returns raw JSON response as dict.
    """
    token = await get_access_token()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}{endpoint}",
            params=params or {},
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 401:
            # Token expired → retry once
            _token_cache["access_token"] = None
            _token_cache["expires_at"] = None
            token = await get_access_token()

            response = await client.get(
                f"{BASE_URL}{endpoint}",
                params=params or {},
                headers={"Authorization": f"Bearer {token}"}
            )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise RuntimeError(
                f"Amadeus API contract violation: expected dict, got {type(data)}"
            )

        return data

async def amadeus_post(endpoint: str, body: Optional[Dict[str, Any]] = None) -> Any:
    """
    Make POST request to Amadeus API.
    
    Args:
        endpoint: API endpoint
        body: Request body (JSON)
    
    Returns:
        API response data
    """
    token = await get_access_token()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}{endpoint}",
            json=body or {},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            return result.get("data", result)
        
        # Handle errors
        logger.error(f"Amadeus POST {endpoint} failed: {response.status_code}")
        try:
            error_data = response.json()
            errors = error_data.get("errors", [])
            if errors:
                error_msg = errors[0].get("detail", str(errors[0]))
                raise Exception(f"Amadeus API Error: {error_msg}")
        except:
            pass
        raise Exception(f"Amadeus API Error: {response.status_code} - {response.text[:200]}")


async def amadeus_delete(endpoint: str) -> Any:
    """
    Make DELETE request to Amadeus API.
    
    Args:
        endpoint: API endpoint
    
    Returns:
        API response or empty dict on success
    """
    token = await get_access_token()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code in [200, 204]:
            if response.text:
                return response.json().get("data", {})
            return {}
        
        logger.error(f"Amadeus DELETE {endpoint} failed: {response.status_code}")
        raise Exception(f"Amadeus API Error: {response.status_code}")


# ═══════════════════════════════════════════════════════════════════
# HIGH-LEVEL HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def search_flights_logic(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    return_date: Optional[str] = None,
    travel_class: str = "ECONOMY",
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Search for flights.
    
    Args:
        origin: Origin airport/city code (e.g., 'PAR')
        destination: Destination airport/city code (e.g., 'LON')
        departure_date: Departure date (YYYY-MM-DD)
        adults: Number of adult passengers
        return_date: Return date for round trip (optional)
        travel_class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
        max_results: Maximum number of results
    
    Returns:
        Dict with 'count' and 'flights' list
    """
    params = {
        "originLocationCode": origin.upper(),
        "destinationLocationCode": destination.upper(),
        "departureDate": departure_date,
        "adults": adults,
        "travelClass": travel_class,
        "max": max_results
    }
    if return_date:
        params["returnDate"] = return_date
    
    data = await amadeus_get("/v2/shopping/flight-offers", params)
    return {"count": len(data) if isinstance(data, list) else 0, "flights": data}


async def search_hotels_by_city_logic(
    city_code: str,
    radius: int = 5,
    ratings: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search for hotels in a city.
    
    Args:
        city_code: City IATA code (e.g., 'PAR')
        radius: Search radius in KM
        ratings: Filter by star ratings (e.g., '3,4,5')
    
    Returns:
        Dict with 'count' and 'hotels' list
    """
    params = {
        "cityCode": city_code.upper(),
        "radius": radius,
        "radiusUnit": "KM"
    }
    if ratings:
        params["ratings"] = ratings
    
    data = await amadeus_get("/v1/reference-data/locations/hotels/by-city", params)
    return {"count": len(data) if isinstance(data, list) else 0, "hotels": data}


async def search_locations_logic(keyword: str) -> Dict[str, Any]:
    """
    Search for airports and cities.
    
    Args:
        keyword: Search term
    
    Returns:
        Dict with 'count' and 'locations' list
    """
    data = await amadeus_get("/v1/reference-data/locations", {
        "keyword": keyword,
        "subType": "CITY,AIRPORT"
    })
    return {"count": len(data) if isinstance(data, list) else 0, "locations": data}


async def get_hotel_offers_logic(
    hotel_ids: List[str],
    check_in: str,
    check_out: str,
    adults: int = 1,
    rooms: int = 1,
    currency: str = "EUR"
) -> Dict[str, Any]:
    """
    Get hotel offers with prices.
    
    Args:
        hotel_ids: List of Amadeus hotel IDs
        check_in: Check-in date (YYYY-MM-DD)
        check_out: Check-out date (YYYY-MM-DD)
        adults: Number of adults
        rooms: Number of rooms
        currency: Currency code
    
    Returns:
        Dict with 'count' and 'offers' list
    """
    data = await amadeus_get("/v3/shopping/hotel-offers", {
        "hotelIds": ",".join(hotel_ids),
        "checkInDate": check_in,
        "checkOutDate": check_out,
        "adults": adults,
        "roomQuantity": rooms,
        "currency": currency
    })
    return {"count": len(data) if isinstance(data, list) else 0, "offers": data}