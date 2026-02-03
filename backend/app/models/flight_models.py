# backend/app/models/flight_models.py
from typing import List, Optional
from pydantic import BaseModel


class FlightSegment(BaseModel):
    origin: str
    destination: str
    departure: str
    arrival: str
    carrier: str
    flight_number: str
    duration: str


class BaggageInfo(BaseModel):
    quantity: int
    weight: Optional[int] = None
    unit: Optional[str] = None


class FlightOffer(BaseModel):
    offer_id: str
    price: float
    currency: str
    segments: List[FlightSegment]
    baggage: Optional[BaggageInfo]
    fare_brand: Optional[str]


class PricingResponse(BaseModel):
    """Amadeus pricing yanıtı için model."""
    offer_id: str
    total: str
    currency: str
    
    @property
    def price(self) -> float:
        """Sayısal fiyat değerini döner."""
        return float(self.total)


class Passenger(BaseModel):
    id: str                 # "1"
    first_name: str
    last_name: str
    date_of_birth: str      # YYYY-MM-DD
    gender: str             # MALE / FEMALE


class Contact(BaseModel):
    email: str
    phone: str


class BookingResult(BaseModel):
    order_id: str
    status: str            # CONFIRMED / FAILED
    ticketed: bool
    total_price: float
    currency: str
    warnings: list[str] = []


class Ancillary(BaseModel):
    type: str          # BAGGAGE / SEAT
    description: str
    price: float
    currency: str


class SelectedSeat(BaseModel):
    segment_id: str      # Amadeus segment ref
    seat_number: str     # "12A"


class SelectedBaggage(BaseModel):
    quantity: int        # extra bag count