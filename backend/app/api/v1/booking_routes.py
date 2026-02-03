"""
ActionFlow AI - Booking Routes
Rezervasyon oluşturma, listeleme, iptal ve detay görüntüleme API'leri

Demo modunda fake booking oluşturur ve n8n workflow tetikler.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid
import logging
import os

from app.services.integration.n8n_service import n8n_service

router = APIRouter(prefix="/bookings", tags=["Bookings"])
logger = logging.getLogger("ActionFlow-BookingRoutes")

# ═══════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════

class BookingType(str, Enum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    PACKAGE = "package"  # Flight + Hotel

class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class PassengerInfo(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None  # YYYY-MM-DD

class FlightBookingRequest(BaseModel):
    """Uçuş rezervasyonu için request"""
    offer_id: str = Field(..., description="Flight offer ID from search")
    passengers: List[PassengerInfo]
    contact_email: EmailStr
    contact_phone: Optional[str] = None

class HotelBookingRequest(BaseModel):
    """Otel rezervasyonu için request"""
    offer_id: str = Field(..., description="Hotel offer ID from search")
    guest_name: str
    check_in: str  # YYYY-MM-DD
    check_out: str  # YYYY-MM-DD
    guests: int = 1
    contact_email: EmailStr
    special_requests: Optional[str] = None

class PackageBookingRequest(BaseModel):
    """Paket (uçuş + otel) rezervasyonu için request"""
    flight_offer_id: str
    hotel_offer_id: str
    passengers: List[PassengerInfo]
    check_in: str
    check_out: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None

class CancelBookingRequest(BaseModel):
    reason: Optional[str] = None

class BookingResponse(BaseModel):
    success: bool
    booking_id: str
    pnr: str
    status: BookingStatus
    booking_type: BookingType
    total_amount: float
    currency: str = "EUR"
    message: str
    details: Dict[str, Any]
    created_at: datetime

# ═══════════════════════════════════════════════════════════════════
# IN-MEMORY STORAGE (Demo için)
# Production'da PostgreSQL kullanılmalı
# ═══════════════════════════════════════════════════════════════════

# Fake booking storage
_bookings_db: Dict[str, Dict[str, Any]] = {}

def generate_pnr() -> str:
    """6 karakterlik PNR kodu üret"""
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_booking_id() -> str:
    """Unique booking ID üret"""
    return f"BK{uuid.uuid4().hex[:8].upper()}"

# ═══════════════════════════════════════════════════════════════════
# FLIGHT BOOKING
# ═══════════════════════════════════════════════════════════════════

@router.post("/flight", response_model=BookingResponse)
async def create_flight_booking(
    request: FlightBookingRequest,
    background_tasks: BackgroundTasks
):
    """
    Uçuş rezervasyonu oluştur (Demo mode)
    
    Production'da Amadeus Flight Orders API kullanılmalı.
    Demo'da fake booking oluşturur ve n8n ile email gönderir.
    """
    logger.info(f"✈️ Creating flight booking for offer: {request.offer_id}")
    
    booking_id = generate_booking_id()
    pnr = generate_pnr()
    
    # Demo için fake fiyat ve detaylar
    # Gerçek implementasyonda offer cache'den alınmalı
    fake_price = 299.00 * len(request.passengers)
    
    booking_data = {
        "id": booking_id,
        "pnr": pnr,
        "booking_type": BookingType.FLIGHT,
        "status": BookingStatus.CONFIRMED,
        "offer_id": request.offer_id,
        "passengers": [p.dict() for p in request.passengers],
        "contact_email": request.contact_email,
        "contact_phone": request.contact_phone,
        "total_amount": fake_price,
        "currency": "EUR",
        "created_at": datetime.utcnow().isoformat(),
        "details": {
            "route": "IST → PAR",  # Demo
            "departure_date": (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "airline": "Turkish Airlines",
            "flight_number": "TK1823",
            "departure_time": "08:30",
            "arrival_time": "11:45",
            "class": "Economy"
        }
    }
    
    # Store booking
    _bookings_db[booking_id] = booking_data
    
    # Trigger n8n workflow in background
    background_tasks.add_task(
        trigger_booking_confirmation,
        booking_data=booking_data,
        booking_type="flight"
    )
    
    logger.info(f"✅ Flight booking created: {booking_id} (PNR: {pnr})")
    
    return BookingResponse(
        success=True,
        booking_id=booking_id,
        pnr=pnr,
        status=BookingStatus.CONFIRMED,
        booking_type=BookingType.FLIGHT,
        total_amount=fake_price,
        currency="EUR",
        message=f"Flight booking confirmed! Your PNR is {pnr}. Confirmation email will be sent shortly.",
        details=booking_data["details"],
        created_at=datetime.utcnow()
    )

# ═══════════════════════════════════════════════════════════════════
# HOTEL BOOKING
# ═══════════════════════════════════════════════════════════════════

@router.post("/hotel", response_model=BookingResponse)
async def create_hotel_booking(
    request: HotelBookingRequest,
    background_tasks: BackgroundTasks
):
    """
    Otel rezervasyonu oluştur (Demo mode)
    """
    logger.info(f"🏨 Creating hotel booking for offer: {request.offer_id}")
    
    booking_id = generate_booking_id()
    pnr = generate_pnr()
    
    # Calculate nights
    check_in_date = datetime.strptime(request.check_in, "%Y-%m-%d")
    check_out_date = datetime.strptime(request.check_out, "%Y-%m-%d")
    nights = (check_out_date - check_in_date).days
    
    # Demo pricing
    fake_price = 120.00 * nights
    
    booking_data = {
        "id": booking_id,
        "pnr": pnr,
        "booking_type": BookingType.HOTEL,
        "status": BookingStatus.CONFIRMED,
        "offer_id": request.offer_id,
        "guest_name": request.guest_name,
        "contact_email": request.contact_email,
        "total_amount": fake_price,
        "currency": "EUR",
        "created_at": datetime.utcnow().isoformat(),
        "details": {
            "hotel_name": "Mercure Paris Centre Eiffel",  # Demo
            "city": "Paris",
            "check_in": request.check_in,
            "check_out": request.check_out,
            "nights": nights,
            "guests": request.guests,
            "room_type": "Standard Double Room",
            "special_requests": request.special_requests,
            "address": "20 Rue Jean Rey, 75015 Paris, France"
        }
    }
    
    _bookings_db[booking_id] = booking_data
    
    background_tasks.add_task(
        trigger_booking_confirmation,
        booking_data=booking_data,
        booking_type="hotel"
    )
    
    logger.info(f"✅ Hotel booking created: {booking_id} (PNR: {pnr})")
    
    return BookingResponse(
        success=True,
        booking_id=booking_id,
        pnr=pnr,
        status=BookingStatus.CONFIRMED,
        booking_type=BookingType.HOTEL,
        total_amount=fake_price,
        currency="EUR",
        message=f"Hotel booking confirmed! Your confirmation number is {pnr}. Details sent to your email.",
        details=booking_data["details"],
        created_at=datetime.utcnow()
    )

# ═══════════════════════════════════════════════════════════════════
# PACKAGE BOOKING (Flight + Hotel)
# ═══════════════════════════════════════════════════════════════════

@router.post("/package", response_model=BookingResponse)
async def create_package_booking(
    request: PackageBookingRequest,
    background_tasks: BackgroundTasks
):
    """
    Paket rezervasyonu oluştur (Uçuş + Otel)
    Demo senaryosundaki ana flow bu endpoint'i kullanır.
    """
    logger.info(f"📦 Creating package booking: Flight {request.flight_offer_id} + Hotel {request.hotel_offer_id}")
    
    booking_id = generate_booking_id()
    pnr = generate_pnr()
    
    # Calculate nights
    check_in_date = datetime.strptime(request.check_in, "%Y-%m-%d")
    check_out_date = datetime.strptime(request.check_out, "%Y-%m-%d")
    nights = (check_out_date - check_in_date).days
    
    # Demo pricing
    flight_price = 299.00 * len(request.passengers)
    hotel_price = 120.00 * nights
    total_price = flight_price + hotel_price
    
    # Primary passenger
    primary_passenger = request.passengers[0] if request.passengers else None
    
    booking_data = {
        "id": booking_id,
        "pnr": pnr,
        "booking_type": BookingType.PACKAGE,
        "status": BookingStatus.CONFIRMED,
        "flight_offer_id": request.flight_offer_id,
        "hotel_offer_id": request.hotel_offer_id,
        "passengers": [p.dict() for p in request.passengers],
        "contact_email": request.contact_email,
        "contact_phone": request.contact_phone,
        "total_amount": total_price,
        "currency": "EUR",
        "created_at": datetime.utcnow().isoformat(),
        "details": {
            "flight": {
                "route": "IST → PAR",
                "departure_date": request.check_in,
                "return_date": request.check_out,
                "airline": "Turkish Airlines",
                "outbound_flight": "TK1823",
                "return_flight": "TK1824",
                "departure_time": "08:30",
                "arrival_time": "11:45",
                "price": flight_price
            },
            "hotel": {
                "name": "Mercure Paris Centre Eiffel",
                "city": "Paris",
                "check_in": request.check_in,
                "check_out": request.check_out,
                "nights": nights,
                "room_type": "Standard Double Room",
                "address": "20 Rue Jean Rey, 75015 Paris, France",
                "price": hotel_price
            },
            "passengers_count": len(request.passengers),
            "primary_guest": f"{primary_passenger.first_name} {primary_passenger.last_name}" if primary_passenger else "Guest"
        }
    }
    
    _bookings_db[booking_id] = booking_data
    
    # Trigger n8n workflow
    background_tasks.add_task(
        trigger_booking_confirmation,
        booking_data=booking_data,
        booking_type="package"
    )
    
    logger.info(f"✅ Package booking created: {booking_id} (PNR: {pnr}) - Total: €{total_price}")
    
    return BookingResponse(
        success=True,
        booking_id=booking_id,
        pnr=pnr,
        status=BookingStatus.CONFIRMED,
        booking_type=BookingType.PACKAGE,
        total_amount=total_price,
        currency="EUR",
        message=f"🎉 Your trip to Paris is booked! PNR: {pnr}. Flight + {nights} nights hotel confirmed. Check your email for details.",
        details=booking_data["details"],
        created_at=datetime.utcnow()
    )

# ═══════════════════════════════════════════════════════════════════
# BOOKING MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@router.get("/user/{user_id}")
async def get_user_bookings(
    user_id: str,
    status: Optional[str] = None,
    type: Optional[str] = None
):
    """Kullanıcının rezervasyonlarını listele"""
    
    # Demo: Tüm bookings'i döndür (gerçekte user_id ile filtrelenir)
    bookings = list(_bookings_db.values())
    
    if status and status != "all":
        bookings = [b for b in bookings if b.get("status") == status]
    
    if type and type != "all":
        bookings = [b for b in bookings if b.get("booking_type") == type]
    
    return {
        "success": True,
        "user_id": user_id,
        "count": len(bookings),
        "bookings": bookings
    }

@router.get("/{booking_id}")
async def get_booking_details(booking_id: str):
    """Tek bir rezervasyonun detaylarını getir"""
    
    if booking_id not in _bookings_db:
        raise HTTPException(status_code=404, detail=f"Booking not found: {booking_id}")
    
    booking = _bookings_db[booking_id]
    
    return {
        "success": True,
        "booking": booking
    }

@router.post("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: str,
    request: CancelBookingRequest,
    background_tasks: BackgroundTasks
):
    """Rezervasyonu iptal et"""
    
    if booking_id not in _bookings_db:
        raise HTTPException(status_code=404, detail=f"Booking not found: {booking_id}")
    
    booking = _bookings_db[booking_id]
    
    if booking["status"] == BookingStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Booking is already cancelled")
    
    # Update status
    booking["status"] = BookingStatus.CANCELLED
    booking["cancelled_at"] = datetime.utcnow().isoformat()
    booking["cancellation_reason"] = request.reason
    
    # Calculate refund (demo: full refund)
    refund_amount = booking["total_amount"]
    booking["refund_amount"] = refund_amount
    booking["refund_status"] = "processing"
    
    # Trigger cancellation workflow
    background_tasks.add_task(
        trigger_cancellation_notification,
        booking_data=booking
    )
    
    logger.info(f"❌ Booking cancelled: {booking_id}")
    
    return {
        "success": True,
        "booking_id": booking_id,
        "status": "cancelled",
        "reason": request.reason,
        "refund_amount": refund_amount,
        "currency": booking["currency"],
        "refund_status": "processing",
        "message": f"Booking cancelled. Refund of €{refund_amount} will be processed within 3-5 business days.",
        "policy_applied": "Free cancellation - Full refund"
    }

@router.post("/{booking_id}/modify")
async def modify_booking(
    booking_id: str,
    modification: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Rezervasyonda değişiklik yap"""
    
    if booking_id not in _bookings_db:
        raise HTTPException(status_code=404, detail=f"Booking not found: {booking_id}")
    
    booking = _bookings_db[booking_id]
    
    if booking["status"] != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="Only confirmed bookings can be modified")
    
    # Apply modifications (demo: sadece tarihleri değiştir)
    old_details = booking["details"].copy()
    
    if "check_in" in modification:
        if "hotel" in booking["details"]:
            booking["details"]["hotel"]["check_in"] = modification["check_in"]
        if "flight" in booking["details"]:
            booking["details"]["flight"]["departure_date"] = modification["check_in"]
    
    if "check_out" in modification:
        if "hotel" in booking["details"]:
            booking["details"]["hotel"]["check_out"] = modification["check_out"]
        if "flight" in booking["details"]:
            booking["details"]["flight"]["return_date"] = modification["check_out"]
    
    booking["modified_at"] = datetime.utcnow().isoformat()
    booking["modification_history"] = booking.get("modification_history", [])
    booking["modification_history"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "changes": modification,
        "old_values": old_details
    })
    
    # Trigger modification notification
    background_tasks.add_task(
        trigger_modification_notification,
        booking_data=booking,
        changes=modification
    )
    
    logger.info(f"📝 Booking modified: {booking_id}")
    
    return {
        "success": True,
        "booking_id": booking_id,
        "message": "Booking has been modified successfully. Updated confirmation sent to your email.",
        "updated_details": booking["details"],
        "modification_fee": 0.00  # Demo: ücretsiz değişiklik
    }

# ═══════════════════════════════════════════════════════════════════
# N8N WORKFLOW TRIGGERS
# ═══════════════════════════════════════════════════════════════════

async def trigger_booking_confirmation(booking_data: Dict[str, Any], booking_type: str):
    """n8n booking confirmation workflow'unu tetikle"""
    
    payload = {
        "event": "booking_confirmed",
        "booking_id": booking_data["id"],
        "pnr": booking_data["pnr"],
        "booking_type": booking_type,
        "customer_email": booking_data.get("contact_email"),
        "total_amount": booking_data["total_amount"],
        "currency": booking_data["currency"],
        "details": booking_data["details"],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add passenger info for flights/packages
    if "passengers" in booking_data:
        passengers = booking_data["passengers"]
        if passengers:
            payload["customer_name"] = f"{passengers[0].get('first_name', '')} {passengers[0].get('last_name', '')}".strip()
    elif "guest_name" in booking_data:
        payload["customer_name"] = booking_data["guest_name"]
    
    success = await n8n_service.trigger_workflow("booking-confirmation", payload)
    
    if success:
        logger.info(f"📧 Booking confirmation workflow triggered for {booking_data['id']}")
    else:
        logger.warning(f"⚠️ Failed to trigger confirmation workflow for {booking_data['id']}")

async def trigger_cancellation_notification(booking_data: Dict[str, Any]):
    """n8n cancellation workflow'unu tetikle"""
    
    payload = {
        "event": "booking_cancelled",
        "booking_id": booking_data["id"],
        "pnr": booking_data["pnr"],
        "customer_email": booking_data.get("contact_email"),
        "refund_amount": booking_data.get("refund_amount", 0),
        "currency": booking_data["currency"],
        "reason": booking_data.get("cancellation_reason"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await n8n_service.trigger_workflow("booking-cancellation", payload)
    logger.info(f"📧 Cancellation notification triggered for {booking_data['id']}")

async def trigger_modification_notification(booking_data: Dict[str, Any], changes: Dict[str, Any]):
    """n8n modification workflow'unu tetikle"""
    
    payload = {
        "event": "booking_modified",
        "booking_id": booking_data["id"],
        "pnr": booking_data["pnr"],
        "customer_email": booking_data.get("contact_email"),
        "changes": changes,
        "updated_details": booking_data["details"],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await n8n_service.trigger_workflow("booking-modification", payload)
    logger.info(f"📧 Modification notification triggered for {booking_data['id']}")