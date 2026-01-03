"""
ActionFlow AI - Travel Support API
Single-file FastAPI application with Amadeus integration

Run: uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")
HOSTNAME = os.getenv("AMADEUS_HOSTNAME", "test")
BASE_URL = "https://test.api.amadeus.com" if HOSTNAME == "test" else "https://api.amadeus.com"

# Token cache
_token_cache = {"token": None, "expires": None}


# ═══════════════════════════════════════════════════════════════════
# AMADEUS CLIENT
# ═══════════════════════════════════════════════════════════════════

async def get_token() -> str:
    """Get or refresh access token"""
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
    """GET request to Amadeus API"""
    token = await get_token()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}{endpoint}", params=params, headers={"Authorization": f"Bearer {token}"})
        result = response.json()
        if response.status_code >= 400:
            error = result.get("errors", [{}])[0].get("detail", "API Error")
            raise HTTPException(status_code=response.status_code, detail=error)
        return result.get("data", result)


async def amadeus_post(endpoint: str, data: dict) -> dict:
    """POST request to Amadeus API"""
    token = await get_token()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}{endpoint}", 
            json=data, 
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        result = response.json()
        if response.status_code >= 400:
            error = result.get("errors", [{}])[0].get("detail", "API Error")
            raise HTTPException(status_code=response.status_code, detail=error)
        return result.get("data", result)


async def amadeus_delete(endpoint: str) -> dict:
    """DELETE request to Amadeus API"""
    token = await get_token()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(f"{BASE_URL}{endpoint}", headers={"Authorization": f"Bearer {token}"})
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail="Delete failed")
        return {"success": True}


# ═══════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class HotelOffersRequest(BaseModel):
    hotel_ids: List[str]
    check_in: str
    check_out: str
    adults: int = 1
    rooms: int = 1
    currency: str = "EUR"

class HotelBookingRequest(BaseModel):
    offer_id: str
    guest_first_name: str
    guest_last_name: str
    guest_email: str
    guest_phone: str
    card_number: str
    card_expiry: str

class FlightBookingRequest(BaseModel):
    flight_offer: Dict[str, Any]
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str = "MALE"
    email: str
    phone: str
    passport_number: str
    passport_expiry: str
    nationality: str = "FR"
    address_line: str = "123 Main Street"
    postal_code: str = "75001"
    city: str = "Paris"
    country: str = "FR"


# ═══════════════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="ActionFlow AI - Travel API",
    description="Travel support API with Amadeus integration",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# ═══════════════════════════════════════════════════════════════════
# HEALTH & INFO
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {"name": "ActionFlow AI Travel API", "version": "1.0.0", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy", "amadeus": HOSTNAME}


# ═══════════════════════════════════════════════════════════════════
# HOTEL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/hotels/search/city/{city_code}")
async def search_hotels_by_city(city_code: str, radius: int = 5, ratings: str = None):
    """Search hotels by city code (PAR, LON, IST, AMS, NYC)"""
    params = {"cityCode": city_code.upper(), "radius": radius, "radiusUnit": "KM"}
    if ratings:
        params["ratings"] = ratings
    data = await amadeus_get("/v1/reference-data/locations/hotels/by-city", params)
    return {"count": len(data), "hotels": data}


@app.get("/hotels/search/location")
async def search_hotels_by_location(lat: float, lng: float, radius: int = 5):
    """Search hotels by coordinates"""
    params = {"latitude": lat, "longitude": lng, "radius": radius, "radiusUnit": "KM"}
    data = await amadeus_get("/v1/reference-data/locations/hotels/by-geocode", params)
    return {"count": len(data), "hotels": data}


@app.post("/hotels/offers")
async def get_hotel_offers(request: HotelOffersRequest):
    """Get hotel pricing and availability"""
    params = {
        "hotelIds": ",".join(request.hotel_ids[:20]),
        "checkInDate": request.check_in,
        "checkOutDate": request.check_out,
        "adults": request.adults,
        "roomQuantity": request.rooms,
        "currency": request.currency
    }
    data = await amadeus_get("/v3/shopping/hotel-offers", params)
    return {"count": len(data), "offers": data}


@app.post("/hotels/book")
async def book_hotel(request: HotelBookingRequest):
    """Book a hotel room"""
    booking_data = {
        "data": {
            "type": "hotel-order",
            "guests": [{"tid": 1, "title": "MR", "firstName": request.guest_first_name, 
                       "lastName": request.guest_last_name, "email": request.guest_email, "phone": request.guest_phone}],
            "travelAgent": {"contact": {"email": "booking@actionflow.ai"}},
            "payments": [{"id": 1, "method": "CREDIT_CARD", 
                         "card": {"vendorCode": "VI", "cardNumber": request.card_number, "expiryDate": request.card_expiry}}],
            "rooms": [{"guestIds": [1], "paymentId": 1}]
        }
    }
    data = await amadeus_post(f"/v2/booking/hotel-orders?offerId={request.offer_id}", booking_data)
    return {"booking_id": data.get("id"), "data": data}


@app.get("/hotels/autocomplete")
async def hotel_autocomplete(keyword: str):
    """Hotel name autocomplete"""
    data = await amadeus_get("/v1/reference-data/locations/hotel", {"keyword": keyword, "subType": "HOTEL_GDS"})
    return {"count": len(data), "hotels": data}


# ═══════════════════════════════════════════════════════════════════
# FLIGHT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/flights/search")
async def search_flights(origin: str, destination: str, date: str, adults: int = 1, 
                         return_date: str = None, travel_class: str = None, max_results: int = 10):
    """Search flights"""
    params = {
        "originLocationCode": origin.upper(),
        "destinationLocationCode": destination.upper(),
        "departureDate": date,
        "adults": adults,
        "max": max_results
    }
    if return_date:
        params["returnDate"] = return_date
    if travel_class:
        params["travelClass"] = travel_class
    
    data = await amadeus_get("/v2/shopping/flight-offers", params)
    
    # Get cheapest price
    if data:
        prices = [float(f.get("price", {}).get("total", 0)) for f in data]
        cheapest = min(prices) if prices else 0
    else:
        cheapest = 0
    
    return {"count": len(data), "cheapest": cheapest, "flights": data}


@app.post("/flights/price")
async def price_flight(flight_offer: Dict[str, Any]):
    """Verify and confirm flight price"""
    data = await amadeus_post("/v1/shopping/flight-offers/pricing", {
        "data": {"type": "flight-offers-pricing", "flightOffers": [flight_offer]}
    })
    priced = data.get("flightOffers", [data])[0] if isinstance(data, dict) else data[0]
    return {"price": priced.get("price"), "offer": priced}


@app.post("/flights/book")
async def book_flight(request: FlightBookingRequest):
    """Create flight booking"""
    ticketing_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT23:59:00")
    
    booking_data = {
        "data": {
            "type": "flight-order",
            "flightOffers": [request.flight_offer],
            "travelers": [{
                "id": "1",
                "dateOfBirth": request.date_of_birth,
                "name": {"firstName": request.first_name, "lastName": request.last_name},
                "gender": request.gender,
                "contact": {
                    "emailAddress": request.email,
                    "phones": [{"deviceType": "MOBILE", "countryCallingCode": "33", "number": request.phone}]
                },
                "documents": [{
                    "documentType": "PASSPORT",
                    "number": request.passport_number,
                    "expiryDate": request.passport_expiry,
                    "issuanceCountry": request.nationality,
                    "nationality": request.nationality,
                    "holder": True
                }]
            }],
            "ticketingAgreement": {"option": "DELAY_TO_QUEUE", "dateTime": ticketing_date},
            "contacts": [{
                "addresseeName": {"firstName": request.first_name, "lastName": request.last_name},
                "purpose": "STANDARD",
                "phones": [{"deviceType": "MOBILE", "countryCallingCode": "33", "number": request.phone}],
                "emailAddress": request.email,
                "address": {
                    "lines": [request.address_line],
                    "postalCode": request.postal_code,
                    "cityName": request.city,
                    "countryCode": request.country
                }
            }]
        }
    }
    
    data = await amadeus_post("/v1/booking/flight-orders", booking_data)
    pnr = data.get("associatedRecords", [{}])[0].get("reference") if data.get("associatedRecords") else None
    
    return {"booking_id": data.get("id"), "pnr": pnr, "data": data}


@app.get("/flights/orders/{order_id}")
async def get_flight_order(order_id: str):
    """Get flight order details"""
    data = await amadeus_get(f"/v1/booking/flight-orders/{order_id}")
    return {"order_id": order_id, "data": data}


@app.delete("/flights/orders/{order_id}")
async def cancel_flight_order(order_id: str):
    """Cancel flight order"""
    await amadeus_delete(f"/v1/booking/flight-orders/{order_id}")
    return {"order_id": order_id, "status": "cancelled"}


# ═══════════════════════════════════════════════════════════════════
# ACTIVITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/activities/search")
async def search_activities(lat: float, lng: float, radius: int = 5):
    """Search tours and activities by coordinates"""
    data = await amadeus_get("/v1/shopping/activities", {"latitude": lat, "longitude": lng, "radius": radius})
    return {"count": len(data), "activities": data}


@app.get("/activities/city/{city_code}")
async def get_activities_by_city(city_code: str, radius: int = 10):
    """Get activities by city code"""
    coords = {
        "PAR": (48.8566, 2.3522), "LON": (51.5074, -0.1278), "IST": (41.0082, 28.9784),
        "AMS": (52.3676, 4.9041), "NYC": (40.7128, -74.006), "BCN": (41.3851, 2.1734),
        "ROM": (41.9028, 12.4964), "BER": (52.52, 13.405), "DXB": (25.2048, 55.2708)
    }
    if city_code.upper() not in coords:
        raise HTTPException(status_code=400, detail=f"City not supported. Available: {list(coords.keys())}")
    
    lat, lng = coords[city_code.upper()]
    data = await amadeus_get("/v1/shopping/activities", {"latitude": lat, "longitude": lng, "radius": radius})
    return {"city": city_code.upper(), "count": len(data), "activities": data}


# ═══════════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/locations/search")
async def search_locations(keyword: str):
    """Search airports and cities (autocomplete)"""
    data = await amadeus_get("/v1/reference-data/locations", {"keyword": keyword, "subType": "CITY,AIRPORT"})
    return {"count": len(data), "locations": data}


@app.get("/airlines/{airline_code}/checkin")
async def get_checkin_link(airline_code: str):
    """Get airline check-in link"""
    data = await amadeus_get("/v2/reference-data/urls/checkin-links", {"airlineCode": airline_code.upper()})
    return {"airline": airline_code.upper(), "links": data}


@app.get("/airlines/{airline_code}")
async def get_airline_info(airline_code: str):
    """Get airline information"""
    data = await amadeus_get("/v1/reference-data/airlines", {"airlineCodes": airline_code.upper()})
    if not data:
        raise HTTPException(status_code=404, detail="Airline not found")
    return data[0]


@app.get("/recommendations")
async def get_recommendations(cities: str, country: str = "US"):
    """Get travel recommendations"""
    data = await amadeus_get("/v1/reference-data/recommended-locations", 
                             {"cityCodes": cities.upper(), "travelerCountryCode": country.upper()})
    return {"count": len(data), "recommendations": data}


# ═══════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)