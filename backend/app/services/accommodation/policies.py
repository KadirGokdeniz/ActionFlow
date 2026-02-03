import os
import requests
from typing import Optional
from .hotel_models import HotelPolicy

HOTEL_API_KEY = os.getenv("HOTEL_API_KEY")
HOTEL_API_HOST = os.getenv("HOTEL_API_HOST")

headers = {
    "X-RapidAPI-Key": HOTEL_API_KEY,
    "X-RapidAPI-Host": HOTEL_API_HOST
}

async def get_hotel_policies(hotel_id: int) -> Optional[HotelPolicy]:
    """
    Fetches the specific cancellation, payment, and house rules of a hotel.
    This data will be used by the Info Agent to answer support queries.
    """
    url = f"https://{HOTEL_API_HOST}/v1/hotels/getHotelPolicies"
    querystring = {"hotel_id": str(hotel_id)}

    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json().get("data", {})

        # Extracting cancellation rules
        # Booking API usually returns a list of policy descriptions
        cancellation_data = data.get("cancellation_policies", [])
        rules = [policy.get("description", "") for policy in cancellation_data]

        # Extracting check-in/out times
        arrival_departure = data.get("arrival_departure_info", {})
        
        return HotelPolicy(
            hotel_id=hotel_id,
            cancellation_rules=rules if rules else ["Standard cancellation rules apply."],
            payment_methods=[pm.get("name", "") for pm in data.get("payment_methods", [])],
            checkin_time=arrival_departure.get("checkin_start", "14:00"),
            checkout_time=arrival_departure.get("checkout_until", "12:00"),
            internet_policy=data.get("internet_policiy", {}).get("description"),
            pet_policy=data.get("pet_policy", {}).get("description")
        )
    except Exception as e:
        print(f"Error fetching hotel policies: {e}")
        return None

async def get_hotel_description(hotel_id: int) -> Optional[str]:
    """
    Fetches the textual description of the hotel.
    Useful for RAG (Retrieval Augmented Generation) to give context to the Agent.
    """
    url = f"https://{HOTEL_API_HOST}/v1/hotels/getDescriptionAndInfo"
    querystring = {"hotel_id": str(hotel_id)}

    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        # Returns the main description text
        return response.json().get("data", {}).get("description", "")
    except Exception as e:
        print(f"Error fetching hotel description: {e}")
        return None