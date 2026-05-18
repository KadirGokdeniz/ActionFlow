import os
import httpx

BOOKING_HOST = "booking-com.p.rapidapi.com"
BOOKING_BASE_URL = f"https://{BOOKING_HOST}"


def _get_headers() -> dict:
    api_key = os.getenv("BOOKING_API_KEY")
    if not api_key:
        raise ValueError("BOOKING_API_KEY not set in .env")
    return {
        "x-rapidapi-host": BOOKING_HOST,
        "x-rapidapi-key": api_key,
    }


async def booking_get(path: str, params: dict):
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(
            f"{BOOKING_BASE_URL}{path}",
            headers=_get_headers(),
            params=params
        )
        if r.status_code >= 400:
            raise Exception(f"Booking API error {r.status_code}: {r.text}")
        return r.json()
