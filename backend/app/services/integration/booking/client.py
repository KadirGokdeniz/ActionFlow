import os
import requests

BOOKING_HOST = "booking-com.p.rapidapi.com"
BOOKING_BASE_URL = f"https://{BOOKING_HOST}"

BOOKING_API_KEY = os.getenv("BOOKING_API_KEY")

HEADERS = {
    "x-rapidapi-host": BOOKING_HOST,
    "x-rapidapi-key": BOOKING_API_KEY
}

def booking_get(path: str, params: dict):
    url = f"{BOOKING_BASE_URL}{path}"
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)

    if r.status_code >= 400:
        raise Exception(f"Booking API error {r.status_code}: {r.text}")

    return r.json()
