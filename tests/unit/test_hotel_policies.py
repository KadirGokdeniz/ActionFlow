import pytest
from app.models.hotel_models import HotelPolicy

def test_hotel_policy_content():
    raw_policy = {
        "hotel_id": 999,
        "cancellation_rules": ["Free cancellation until 24h before arrival", "No-show fee 100%"],
        "payment_methods": ["Credit Card", "Cash"],
        "checkin_time": "15:00",
        "checkout_time": "11:00",
        "pet_policy": "Pets are allowed upon request. Charges may apply."
    }
    
    policy = HotelPolicy(**raw_policy)
    
    assert "Free cancellation" in policy.cancellation_rules[0]
    assert policy.checkin_time == "15:00"
    assert "Pets are allowed" in policy.pet_policy
