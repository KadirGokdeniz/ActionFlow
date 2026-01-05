# backend/services.py
import httpx
import os
from datetime import datetime, timedelta
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════
API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")
HOSTNAME = os.getenv("AMADEUS_HOSTNAME", "test")
BASE_URL = "https://test.api.amadeus.com" if HOSTNAME == "test" else "https://api.amadeus.com"

_token_cache = {"token": None, "expires": None}

# ═══════════════════════════════════════════════════════════════════
# AMADEUS CORE CLIENT
# ═══════════════════════════════════════════════════════════════════

async def get_token() -> str:
    if _token_cache["token"] and _token_cache["expires"] and datetime.now() < _token_cache["expires"]:
        return _token_cache["token"]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/security/oauth2/token",
            data={"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": API_SECRET},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Amadeus authentication failed")
        
        data = response.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires"] = datetime.now() + timedelta(seconds=data["expires_in"] - 60)
        return _token_cache["token"]

async def amadeus_get(endpoint: str, params: dict = None) -> dict:
    token = await get_token()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}{endpoint}", params=params, headers={"Authorization": f"Bearer {token}"})
        result = response.json()
        if response.status_code >= 400:
            error = result.get("errors", [{}])[0].get("detail", "API Error")
            raise HTTPException(status_code=response.status_code, detail=error)
        return result.get("data", result)

async def amadeus_post(endpoint: str, data: dict) -> dict:
    token = await get_token()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}{endpoint}", json=data, 
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        result = response.json()
        if response.status_code >= 400:
            error = result.get("errors", [{}])[0].get("detail", "API Error")
            raise HTTPException(status_code=response.status_code, detail=error)
        return result.get("data", result)

async def amadeus_delete(endpoint: str) -> dict:
    """
    Cancel an existing booking or order in the Amadeus system.
    Args:
        endpoint: The full API endpoint for the specific order to be deleted (e.g. '/v1/booking/flight-orders/123')
    """
    token = await get_token()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(f"{BASE_URL}{endpoint}", headers={"Authorization": f"Bearer {token}"})
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail="Delete failed")
        return {"success": True}

# ═══════════════════════════════════════════════════════════════════
# BUSINESS LOGIC (İş Mantığı Fonksiyonları)
# ═══════════════════════════════════════════════════════════════════

async def search_flights_logic(origin: str, destination: str, date: str, adults: int = 1, 
                         return_date: str = None, travel_class: str = None, max_results: int = 10):
    """
    Search for flight offers between two cities on a specific date.
    Args:
        origin: IATA code of the departure city (e.g. 'PAR')
        destination: IATA code of the destination city (e.g. 'NYC')
        date: Departure date in YYYY-MM-DD format
    """
    params = {
        "originLocationCode": origin.upper(),
        "destinationLocationCode": destination.upper(),
        "departureDate": date,
        "adults": adults,
        "max": max_results
    }
    if return_date: params["returnDate"] = return_date
    if travel_class: params["travelClass"] = travel_class
    
    return await amadeus_get("/v2/shopping/flight-offers", params)

async def search_hotels_by_city_logic(city_code: str, radius: int = 5, ratings: str = None):
    """
    Search for hotels in a specific city using its IATA code.
    Args:
        city_code: IATA code of the city (e.g. 'PAR' for Paris)
        radius: Search radius in kilometers (default: 5)
    """
    params = {"cityCode": city_code.upper(), "radius": radius, "radiusUnit": "KM"}
    if ratings: params["ratings"] = ratings
    return await amadeus_get("/v1/reference-data/locations/hotels/by-city", params)