from pydantic import BaseModel
from typing import List, Optional


class HotelDestination(BaseModel):
    dest_id: str
    search_type: str
    city_name: str
    country: str
    label: Optional[str] = None


class HotelOffer(BaseModel):
    hotel_id: int
    hotel_name: str
    main_photo_url: Optional[str] = None
    price: float
    currency: str = "EUR"
    review_score: Optional[float] = None
    review_score_word: Optional[str] = None
    checkin_date: str
    checkout_date: str
    distance_from_center: Optional[str] = None


class HotelPolicy(BaseModel):
    hotel_id: int
    cancellation_rules: List[str]
    payment_methods: List[str]
    checkin_time: str
    checkout_time: str
    internet_policy: Optional[str] = None
    pet_policy: Optional[str] = None


class HotelRoom(BaseModel):
    room_id: str
    room_name: str
    bed_type: Optional[str] = None
    is_available: bool = True