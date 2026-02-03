import pytest
from app.models.hotel_models import HotelOffer, HotelDestination
from app.services.accommodation.hotel_tools import get_hotel_destination # Assuming logic is similar to Amadeus

def test_map_hotel_destination():
    # Mocking a raw response from Booking.com searchDestination
    raw_dest = {
        "dest_id": "city:-2140479",
        "search_type": "city",
        "city_name": "Amsterdam",
        "country": "Netherlands",
        "label": "Amsterdam, North Holland, Netherlands"
    }
    
    # Manually creating the model (Testing the Pydantic validation)
    dest = HotelDestination(**raw_dest)
    
    assert dest.dest_id == "city:-2140479"
    assert dest.city_name == "Amsterdam"
    assert dest.country == "Netherlands"

def test_hotel_offer_mapping():
    # Mocking raw hotel data from searchHotels
    raw_hotel = {
        "hotel_id": 12345,
        "hotel_name": "Grand Central Hotel",
        "price": 145.50,
        "currency": "EUR",
        "review_score": 8.5,
        "checkin_date": "2026-05-12",
        "checkout_date": "2026-05-15"
    }
    
    offer = HotelOffer(**raw_hotel)
    
    assert offer.hotel_id == 12345
    assert offer.price == 145.50
    assert offer.currency == "EUR"
    assert offer.review_score == 8.5
