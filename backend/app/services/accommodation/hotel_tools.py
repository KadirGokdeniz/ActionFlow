"""
Booking.com API Integration via RapidAPI
ActionFlow AI - Hotel Tools

RapidAPI Endpoint: booking-com15.p.rapidapi.com
"""

import os
import httpx
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# RapidAPI Configuration
RAPIDAPI_KEY = os.getenv("HOTEL_API_KEY") or os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("HOTEL_API_HOST", "booking-com15.p.rapidapi.com")
BASE_URL = f"https://{RAPIDAPI_HOST}"

# Headers for RapidAPI
def get_headers():
    if not RAPIDAPI_KEY:
        raise ValueError("HOTEL_API_KEY or RAPIDAPI_KEY not set in .env")
    return {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }


async def get_hotel_destination(city_name: str) -> Optional[Dict[str, Any]]:
    """
    Converts a city name into a Booking.com Destination ID.
    
    Args:
        city_name: Name of the city (e.g., "London", "Paris", "Istanbul")
    
    Returns:
        Dictionary with dest_id, city_name, country, etc.
    """
    # Eğer API key yoksa mock data kullan
    if not RAPIDAPI_KEY:
        print("⚠️ HOTEL_API_KEY not set, using mock data")
        return await get_hotel_destination_mock(city_name)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/hotels/searchDestination",
                headers=get_headers(),
                params={"query": city_name}
            )
            response.raise_for_status()
            data = response.json()
            
            # Return first matching destination
            if data and isinstance(data, list) and len(data) > 0:
                dest = data[0]
                return {
                    "dest_id": dest.get("dest_id"),
                    "search_type": dest.get("search_type", "city"),
                    "city_name": dest.get("city_name") or dest.get("name"),
                    "country": dest.get("country"),
                    "label": dest.get("label"),
                    "region": dest.get("region"),
                    "hotels_count": dest.get("hotels"),
                    "type": dest.get("dest_type")
                }
            return None
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP error searching destination: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"Error searching destination: {e}")
        return None


async def search_hotels(
    dest_id: str,
    arrival_date: str,
    departure_date: str,
    adults: int = 1,
    room_qty: int = 1,
    currency: str = "EUR",
    page: int = 1
) -> List[Dict[str, Any]]:
    """
    Search for available hotels on Booking.com.
    
    Args:
        dest_id: Booking.com destination ID (from get_hotel_destination)
        arrival_date: Check-in date (YYYY-MM-DD)
        departure_date: Check-out date (YYYY-MM-DD)
        adults: Number of adults
        room_qty: Number of rooms
        currency: Currency code (EUR, USD, etc.)
        page: Page number for pagination
    
    Returns:
        List of hotel offers with prices
    """
    # Eğer API key yoksa mock data kullan
    if not RAPIDAPI_KEY:
        print("⚠️ HOTEL_API_KEY not set, using mock data")
        return await search_hotels_mock(dest_id, arrival_date, departure_date, adults)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/hotels/searchHotels",
                headers=get_headers(),
                params={
                    "dest_id": dest_id,
                    "search_type": "city",
                    "arrival_date": arrival_date,
                    "departure_date": departure_date,
                    "adults": adults,
                    "room_qty": room_qty,
                    "currency_code": currency,
                    "page_number": page,
                    "units": "metric",
                    "temperature_unit": "c",
                    "languagecode": "en-us"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            hotels = data.get("data", {}).get("hotels", [])
            
            # Transform to our format
            results = []
            for hotel in hotels:
                property_data = hotel.get("property", {})
                price_data = property_data.get("priceBreakdown", {})
                
                results.append({
                    "hotel_id": property_data.get("id"),
                    "name": property_data.get("name"),
                    "rating": property_data.get("reviewScore"),
                    "review_count": property_data.get("reviewCount"),
                    "stars": property_data.get("propertyClass"),
                    "location": {
                        "latitude": property_data.get("latitude"),
                        "longitude": property_data.get("longitude"),
                        "address": property_data.get("wishlistName")
                    },
                    "price": {
                        "amount": price_data.get("grossPrice", {}).get("value"),
                        "currency": price_data.get("grossPrice", {}).get("currency"),
                        "per_night": price_data.get("grossPrice", {}).get("value")
                    },
                    "photo_url": property_data.get("photoUrls", [""])[0] if property_data.get("photoUrls") else None,
                    "checkin": property_data.get("checkin", {}).get("fromTime"),
                    "checkout": property_data.get("checkout", {}).get("untilTime"),
                    "free_cancellation": property_data.get("isPreferred", False)
                })
            
            return results
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP error searching hotels: {e.response.status_code}")
        return []
    except Exception as e:
        print(f"Error searching hotels: {e}")
        return []


async def get_hotel_details(hotel_id: int, arrival_date: str, departure_date: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific hotel.
    
    Args:
        hotel_id: Booking.com hotel ID
        arrival_date: Check-in date
        departure_date: Check-out date
    
    Returns:
        Hotel details including description, amenities, etc.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/hotels/getHotelDetails",
                headers=get_headers(),
                params={
                    "hotel_id": hotel_id,
                    "arrival_date": arrival_date,
                    "departure_date": departure_date,
                    "currency_code": "EUR",
                    "languagecode": "en-us"
                }
            )
            response.raise_for_status()
            return response.json()
            
    except Exception as e:
        print(f"Error getting hotel details: {e}")
        return None


# ============================================================
# MOCK DATA: For testing without API key
# ============================================================

async def get_hotel_destination_mock(city_name: str) -> Optional[Dict[str, Any]]:
    """Mock destination data for testing"""
    mock_destinations = {
        "london": {"dest_id": "-2601889", "city_name": "London", "country": "United Kingdom", "search_type": "city"},
        "paris": {"dest_id": "-1456928", "city_name": "Paris", "country": "France", "search_type": "city"},
        "amsterdam": {"dest_id": "-2140479", "city_name": "Amsterdam", "country": "Netherlands", "search_type": "city"},
        "istanbul": {"dest_id": "-755070", "city_name": "Istanbul", "country": "Turkey", "search_type": "city"},
        "barcelona": {"dest_id": "-372490", "city_name": "Barcelona", "country": "Spain", "search_type": "city"},
        "rome": {"dest_id": "-126693", "city_name": "Rome", "country": "Italy", "search_type": "city"},
        "berlin": {"dest_id": "-1746443", "city_name": "Berlin", "country": "Germany", "search_type": "city"},
        "new york": {"dest_id": "20088325", "city_name": "New York", "country": "United States", "search_type": "city"},
        "dubai": {"dest_id": "-782831", "city_name": "Dubai", "country": "United Arab Emirates", "search_type": "city"},
    }
    return mock_destinations.get(city_name.lower())


async def search_hotels_mock(dest_id: str, arrival_date: str, departure_date: str, adults: int = 1) -> List[Dict[str, Any]]:
    """Mock hotel search for testing"""
    return [
        {
            "hotel_id": 12345,
            "name": "Grand Hotel Central",
            "rating": 8.5,
            "review_count": 1234,
            "stars": 4,
            "location": {
                "latitude": 52.3676,
                "longitude": 4.9041,
                "address": "City Center"
            },
            "price": {"amount": 145.00, "currency": "EUR", "per_night": 145.00},
            "photo_url": "https://example.com/hotel1.jpg",
            "checkin": "15:00",
            "checkout": "11:00",
            "free_cancellation": True
        },
        {
            "hotel_id": 12346,
            "name": "Budget Inn Downtown",
            "rating": 7.2,
            "review_count": 567,
            "stars": 3,
            "location": {
                "latitude": 52.3700,
                "longitude": 4.8900,
                "address": "Downtown"
            },
            "price": {"amount": 89.00, "currency": "EUR", "per_night": 89.00},
            "photo_url": "https://example.com/hotel2.jpg",
            "checkin": "14:00",
            "checkout": "10:00",
            "free_cancellation": False
        },
        {
            "hotel_id": 12347,
            "name": "Luxury Palace Hotel",
            "rating": 9.2,
            "review_count": 2345,
            "stars": 5,
            "location": {
                "latitude": 52.3650,
                "longitude": 4.9100,
                "address": "Premium District"
            },
            "price": {"amount": 289.00, "currency": "EUR", "per_night": 289.00},
            "photo_url": "https://example.com/hotel3.jpg",
            "checkin": "16:00",
            "checkout": "12:00",
            "free_cancellation": True
        }
    ]