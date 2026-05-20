"""
Amadeus API Client with retry + circuit breaker.
"""
import asyncio
import os
import time
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger("AmadeusClient")

API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")
HOSTNAME = os.getenv("AMADEUS_HOSTNAME", "test.api.amadeus.com")
BASE_URL = f"https://{HOSTNAME}"

_token_cache = {"access_token": None, "expires_at": None}


# ?? Custom exception ??????????????????????????????????????????????????????????

class AmadeusServiceError(Exception):
    """Raised when Amadeus is unavailable after retries or circuit breaker is open."""
    pass


# ?? Circuit breaker ???????????????????????????????????????????????????????????

CB_FAILURE_THRESHOLD = 5
CB_RECOVERY_TIMEOUT = 60  # seconds

_cb = {"failures": 0, "last_failure": 0.0, "is_open": False}

RETRYABLE = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)


def _cb_is_open() -> bool:
    if _cb["is_open"]:
        if time.monotonic() - _cb["last_failure"] > CB_RECOVERY_TIMEOUT:
            _cb["is_open"] = False
            _cb["failures"] = 0
            logger.info("Circuit breaker: half-open, allowing one request through")
            return False
        return True
    return False


def _cb_failure():
    _cb["failures"] += 1
    _cb["last_failure"] = time.monotonic()
    if _cb["failures"] >= CB_FAILURE_THRESHOLD:
        _cb["is_open"] = True
        logger.warning(
            f"Circuit breaker OPEN: Amadeus unreachable after "
            f"{CB_FAILURE_THRESHOLD} failures. Retry in {CB_RECOVERY_TIMEOUT}s."
        )


def _cb_success():
    if _cb["failures"]:
        logger.info("Circuit breaker: success, resetting")
    _cb["failures"] = 0
    _cb["is_open"] = False


# ?? Auth ??????????????????????????????????????????????????????????????????????

async def get_access_token() -> str:
    global _token_cache
    if _token_cache["access_token"] and _token_cache["expires_at"]:
        if datetime.now() < _token_cache["expires_at"]:
            return _token_cache["access_token"]

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
            raise Exception(f"Failed to get Amadeus token: {response.status_code}")

        data = response.json()
        _token_cache["access_token"] = data["access_token"]
        expires_in = data.get("expires_in", 1799) - 60
        _token_cache["expires_at"] = datetime.now() + timedelta(seconds=expires_in)
        return _token_cache["access_token"]


# ?? Retry helper ??????????????????????????????????????????????????????????????

async def _retry_request(operation_name: str, fn, max_attempts: int = 3):
    """Execute fn with exponential backoff retry. Raises AmadeusServiceError on exhaustion."""
    if _cb_is_open():
        raise AmadeusServiceError(
            f"Amadeus circuit breaker is open. Service unavailable for ~{CB_RECOVERY_TIMEOUT}s."
        )

    last_exc = None
    for attempt in range(max_attempts):
        try:
            result = await fn()
            _cb_success()
            return result
        except RETRYABLE as e:
            last_exc = e
            _cb_failure()
            if attempt < max_attempts - 1:
                wait = 2 ** attempt  # 1s, 2s
                logger.warning(
                    f"Amadeus {operation_name} attempt {attempt+1} failed: {e}. "
                    f"Retrying in {wait}s..."
                )
                await asyncio.sleep(wait)
        except Exception:
            _cb_failure()
            raise

    raise AmadeusServiceError(
        f"Amadeus {operation_name} unavailable after {max_attempts} attempts: {last_exc}"
    ) from last_exc


# ?? HTTP methods ??????????????????????????????????????????????????????????????

async def amadeus_get(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Make GET request to Amadeus API.
    Returns the full raw JSON response dict.
    Callers must access response["data"] themselves.
    """
    async def _do():
        token = await get_access_token()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}{endpoint}",
                params=params or {},
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 401:
                _token_cache["access_token"] = None
                _token_cache["expires_at"] = None
                token2 = await get_access_token()
                response = await client.get(
                    f"{BASE_URL}{endpoint}",
                    params=params or {},
                    headers={"Authorization": f"Bearer {token2}"}
                )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise RuntimeError(f"Amadeus contract violation: expected dict, got {type(data)}")
            return data

    return await _retry_request(f"GET {endpoint}", _do)


async def amadeus_post(endpoint: str, body: Optional[Dict[str, Any]] = None) -> Any:
    """
    Make POST request to Amadeus API.
    Returns response["data"] unwrapped (unlike amadeus_get which returns full response).
    Callers access fields directly (e.g. response.get("flightOffers")).
    """
    async def _do():
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
            logger.error(f"Amadeus POST {endpoint} failed: {response.status_code}")
            try:
                errors = response.json().get("errors", [])
                if errors:
                    raise Exception(f"Amadeus API Error: {errors[0].get('detail', str(errors[0]))}")
            except Exception:
                pass
            raise Exception(f"Amadeus API Error: {response.status_code} - {response.text[:200]}")

    return await _retry_request(f"POST {endpoint}", _do)


async def amadeus_delete(endpoint: str) -> Any:
    async def _do():
        token = await get_access_token()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{BASE_URL}{endpoint}",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code in [200, 204]:
                return response.json().get("data", {}) if response.text else {}
            raise Exception(f"Amadeus DELETE failed: {response.status_code}")

    return await _retry_request(f"DELETE {endpoint}", _do)


# ?? High-level helpers (unchanged) ????????????????????????????????????????????

async def search_flights_logic(
    origin: str, destination: str, departure_date: str,
    adults: int = 1, return_date: Optional[str] = None,
    travel_class: str = "ECONOMY", max_results: int = 10
) -> Dict[str, Any]:
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
    city_code: str, radius: int = 5, ratings: Optional[str] = None
) -> Dict[str, Any]:
    params = {"cityCode": city_code.upper(), "radius": radius, "radiusUnit": "KM"}
    if ratings:
        params["ratings"] = ratings
    data = await amadeus_get("/v1/reference-data/locations/hotels/by-city", params)
    return {"count": len(data) if isinstance(data, list) else 0, "hotels": data}


async def search_locations_logic(keyword: str) -> Dict[str, Any]:
    data = await amadeus_get("/v1/reference-data/locations", {
        "keyword": keyword,
        "subType": "CITY,AIRPORT"
    })
    return {"count": len(data) if isinstance(data, list) else 0, "locations": data}


async def get_hotel_offers_logic(
    hotel_ids: List[str], check_in: str, check_out: str,
    adults: int = 1, rooms: int = 1, currency: str = "EUR"
) -> Dict[str, Any]:
    data = await amadeus_get("/v3/shopping/hotel-offers", {
        "hotelIds": ",".join(hotel_ids),
        "checkInDate": check_in,
        "checkOutDate": check_out,
        "adults": adults,
        "roomQuantity": rooms,
        "currency": currency
    })
    return {"count": len(data) if isinstance(data, list) else 0, "offers": data}
