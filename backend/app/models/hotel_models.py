"""
Accommodation (Hotel) modelleri - Booking.com API entegrasyonu için.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class HotelDestination(BaseModel):
    """Amadeus'tan gelen şehir bilgisini Booking ID'sine eşlemek için kullanılır."""
    dest_id: str
    search_type: str  # 'city' veya 'landmark'
    city_name: str
    country: str
    label: Optional[str] = None  # Kullanıcıya gösterilecek tam isim (Örn: "Amsterdam, Netherlands")


class HotelOffer(BaseModel):
    """Arama sonuçlarında listelenecek otel özeti."""
    hotel_id: int
    hotel_name: str
    main_photo_url: Optional[str] = None
    price: float
    currency: str = "EUR"
    review_score: Optional[float] = None
    review_score_word: Optional[str] = None  # "Excellent", "Very Good" vb.
    checkin_date: str
    checkout_date: str
    distance_from_center: Optional[str] = None


class HotelPolicy(BaseModel):
    """Info Agent'ın RAG için kullanacağı iptal ve kural bilgileri."""
    hotel_id: int
    cancellation_rules: List[str]
    payment_methods: List[str]
    checkin_time: str
    checkout_time: str
    internet_policy: Optional[str] = None
    pet_policy: Optional[str] = None


class HotelRoom(BaseModel):
    """Oda seçimi aşaması için model."""
    room_id: str
    room_name: str
    bed_type: Optional[str] = None
    is_available: bool = True
    max_occupancy: Optional[int] = None
    price_per_night: Optional[float] = None
    currency: str = "EUR"
    amenities: List[str] = []


class HotelBookingRequest(BaseModel):
    """Otel rezervasyonu için istek modeli."""
    hotel_id: int
    room_id: str
    checkin_date: str
    checkout_date: str
    guest_first_name: str
    guest_last_name: str
    guest_email: str
    guest_phone: str
    special_requests: Optional[str] = None
    num_adults: int = 1
    num_children: int = 0


class HotelBookingResponse(BaseModel):
    """Otel rezervasyonu sonuç modeli."""
    booking_id: str
    hotel_id: int
    hotel_name: str
    status: str  # CONFIRMED, PENDING, FAILED
    confirmation_number: Optional[str] = None
    total_price: float
    currency: str = "EUR"
    checkin_date: str
    checkout_date: str
    guest_name: str
    cancellation_deadline: Optional[str] = None