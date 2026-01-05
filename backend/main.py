"""
ActionFlow AI - Travel Support API
FastAPI + Amadeus + PostgreSQL/pgvector

Run: uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import httpx
import os
import uuid
from dotenv import load_dotenv

# Database imports
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import (
    get_db, init_db,
    User, Conversation, Message, Booking, Policy,
    ChannelType, BookingType, BookingStatus, ConversationStatus,
    vector_search
)

# Services and Orchestrator imports
# Import business logic from services instead of defining it here
from services import (
    amadeus_get, amadeus_post, amadeus_delete,
    search_flights_logic, search_hotels_by_city_logic,
    HOSTNAME # For health check info
)
from orchestrator import build_graph
from langchain_core.messages import HumanMessage

load_dotenv()

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
    user_id: Optional[str] = None  # Link to ActionFlow user

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
    user_id: Optional[str] = None

# New schemas for database operations
class UserCreate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: str
    last_name: str
    preferred_language: str = "en"

class ConversationCreate(BaseModel):
    user_id: Optional[str] = None
    channel: str = "web"
    intent: Optional[str] = None

class MessageCreate(BaseModel):
    conversation_id: str
    role: str  # user, assistant, system
    content: str
    is_voice: bool = False
    agent_type: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    await init_db()
    yield

app = FastAPI(
    title="ActionFlow AI - Travel API",
    description="Travel support API with Amadeus + PostgreSQL",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# ═══════════════════════════════════════════════════════════════════
# HEALTH & INFO
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {"name": "ActionFlow AI Travel API", "version": "2.0.0", "database": "PostgreSQL + pgvector", "docs": "/docs"}

@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    # Check database connection
    try:
        await db.execute(select(func.count()).select_from(User))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {"status": "healthy", "amadeus": HOSTNAME, "database": db_status}


# ═══════════════════════════════════════════════════════════════════
# USER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/users")
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user"""
    db_user = User(
        id=str(uuid.uuid4()),
        email=user.email,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        preferred_language=user.preferred_language
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return {"id": db_user.id, "email": db_user.email, "name": f"{db_user.first_name} {db_user.last_name}"}


@app.get("/users/{user_id}")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "name": f"{user.first_name} {user.last_name}",
        "language": user.preferred_language,
        "tier": user.tier
    }


@app.get("/users/{user_id}/bookings")
async def get_user_bookings(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get all bookings for a user"""
    result = await db.execute(
        select(Booking).where(Booking.user_id == user_id).order_by(Booking.booked_at.desc())
    )
    bookings = result.scalars().all()
    return {
        "count": len(bookings),
        "bookings": [
            {
                "id": b.id,
                "type": b.booking_type.value,
                "status": b.status.value,
                "external_id": b.external_id,
                "pnr": b.pnr,
                "amount": b.total_amount,
                "currency": b.currency,
                "travel_date": b.travel_date.isoformat() if b.travel_date else None,
                "booked_at": b.booked_at.isoformat()
            }
            for b in bookings
        ]
    }


# ═══════════════════════════════════════════════════════════════════
# CONVERSATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/conversations")
async def create_conversation(conv: ConversationCreate, db: AsyncSession = Depends(get_db)):
    """Start a new conversation"""
    db_conv = Conversation(
        id=str(uuid.uuid4()),
        user_id=conv.user_id,
        channel=ChannelType(conv.channel),
        intent=conv.intent,
        status=ConversationStatus.ACTIVE
    )
    db.add(db_conv)
    await db.commit()
    await db.refresh(db_conv)
    return {"id": db_conv.id, "channel": db_conv.channel.value, "status": db_conv.status.value}


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get conversation with messages"""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get messages
    msg_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()
    
    return {
        "id": conv.id,
        "user_id": conv.user_id,
        "channel": conv.channel.value,
        "status": conv.status.value,
        "intent": conv.intent,
        "urgency": conv.urgency_score,
        "messages": [
            {"role": m.role, "content": m.content, "agent": m.agent_type, "created_at": m.created_at.isoformat()}
            for m in messages
        ]
    }


@app.post("/conversations/{conversation_id}/messages")
async def add_message(conversation_id: str, msg: MessageCreate, db: AsyncSession = Depends(get_db)):
    """Add message to conversation"""
    # Verify conversation exists
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    db_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=msg.role,
        content=msg.content,
        is_voice=msg.is_voice,
        agent_type=msg.agent_type
    )
    db.add(db_msg)
    
    # Update conversation transcript
    conv.transcript = (conv.transcript or "") + f"\n{msg.role}: {msg.content}"
    conv.updated_at = datetime.utcnow()
    
    await db.commit()
    return {"id": db_msg.id, "created_at": db_msg.created_at.isoformat()}


# ═══════════════════════════════════════════════════════════════════
# POLICY ENDPOINTS (RAG)
# ═══════════════════════════════════════════════════════════════════

@app.get("/policies")
async def list_policies(category: str = None, db: AsyncSession = Depends(get_db)):
    """List all policies, optionally filtered by category"""
    query = select(Policy)
    if category:
        query = query.where(Policy.category == category)
    
    result = await db.execute(query)
    policies = result.scalars().all()
    
    return {
        "count": len(policies),
        "policies": [
            {"id": p.id, "category": p.category, "provider": p.provider, "title": p.title}
            for p in policies
        ]
    }


@app.get("/policies/{policy_id}")
async def get_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    """Get full policy content"""
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return {
        "id": policy.id,
        "category": policy.category,
        "provider": policy.provider,
        "title": policy.title,
        "content": policy.content,
        "source_url": policy.source_url
    }


@app.get("/policies/search/{query}")
async def search_policies(query: str, limit: int = 5, db: AsyncSession = Depends(get_db)):
    """
    Search policies by text (basic search)
    TODO: Implement vector search when embeddings are generated
    """
    result = await db.execute(
        select(Policy).where(
            Policy.content.ilike(f"%{query}%") | Policy.title.ilike(f"%{query}%")
        ).limit(limit)
    )
    policies = result.scalars().all()
    
    return {
        "query": query,
        "count": len(policies),
        "results": [
            {"id": p.id, "category": p.category, "title": p.title, "snippet": p.content[:200]}
            for p in policies
        ]
    }


# ═══════════════════════════════════════════════════════════════════
# HOTEL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/hotels/search/city/{city_code}")
async def search_hotels_by_city(city_code: str, radius: int = 5, ratings: str = None):
    # Logic moved to services.py
    data = await search_hotels_by_city_logic(city_code, radius, ratings)
    return {"count": len(data), "hotels": data}


@app.get("/hotels/search/location")
async def search_hotels_by_location(lat: float, lng: float, radius: int = 5):
    params = {"latitude": lat, "longitude": lng, "radius": radius, "radiusUnit": "KM"}
    data = await amadeus_get("/v1/reference-data/locations/hotels/by-geocode", params)
    return {"count": len(data), "hotels": data}


@app.post("/hotels/offers")
async def get_hotel_offers(request: HotelOffersRequest):
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
async def book_hotel(request: HotelBookingRequest, db: AsyncSession = Depends(get_db)):
    """Book hotel and save to database"""
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
    
    # Save to database if user_id provided
    if request.user_id:
        db_booking = Booking(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            booking_type=BookingType.HOTEL,
            status=BookingStatus.CONFIRMED,
            external_id=data.get("id"),
            details=data,
            currency="EUR",
            total_amount=0,  # Extract from response
            travel_date=datetime.utcnow()  # Extract from response
        )
        db.add(db_booking)
        await db.commit()
    
    return {"booking_id": data.get("id"), "data": data}


@app.get("/hotels/autocomplete")
async def hotel_autocomplete(keyword: str):
    data = await amadeus_get("/v1/reference-data/locations/hotel", {"keyword": keyword, "subType": "HOTEL_GDS"})
    return {"count": len(data), "hotels": data}


# ═══════════════════════════════════════════════════════════════════
# FLIGHT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/flights/search")
async def search_flights(origin: str, destination: str, date: str, adults: int = 1, 
                         return_date: str = None, travel_class: str = None, max_results: int = 10):
    # Logic moved to services.py
    data = await search_flights_logic(origin, destination, date, adults, return_date, travel_class, max_results)
    
    if data:
        prices = [float(f.get("price", {}).get("total", 0)) for f in data]
        cheapest = min(prices) if prices else 0
    else:
        cheapest = 0
    
    return {"count": len(data), "cheapest": cheapest, "flights": data}


@app.post("/flights/price")
async def price_flight(flight_offer: Dict[str, Any]):
    data = await amadeus_post("/v1/shopping/flight-offers/pricing", {
        "data": {"type": "flight-offers-pricing", "flightOffers": [flight_offer]}
    })
    priced = data.get("flightOffers", [data])[0] if isinstance(data, dict) else data[0]
    return {"price": priced.get("price"), "offer": priced}


@app.post("/flights/book")
async def book_flight(request: FlightBookingRequest, db: AsyncSession = Depends(get_db)):
    """Book flight and save to database"""
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
    
    # Save to database if user_id provided
    if request.user_id:
        price = request.flight_offer.get("price", {}).get("total", 0)
        db_booking = Booking(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            booking_type=BookingType.FLIGHT,
            status=BookingStatus.CONFIRMED,
            external_id=data.get("id"),
            pnr=pnr,
            details=data,
            currency=request.flight_offer.get("price", {}).get("currency", "EUR"),
            total_amount=float(price),
            travel_date=datetime.utcnow()  # Extract from flight offer
        )
        db.add(db_booking)
        await db.commit()
    
    return {"booking_id": data.get("id"), "pnr": pnr, "data": data}


@app.get("/flights/orders/{order_id}")
async def get_flight_order(order_id: str):
    data = await amadeus_get(f"/v1/booking/flight-orders/{order_id}")
    return {"order_id": order_id, "data": data}


@app.delete("/flights/orders/{order_id}")
async def cancel_flight_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel flight and update database"""
    # Use service method
    await amadeus_delete(f"/v1/booking/flight-orders/{order_id}")
    
    # Update booking status in database
    result = await db.execute(select(Booking).where(Booking.external_id == order_id))
    booking = result.scalar_one_or_none()
    if booking:
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.utcnow()
        await db.commit()
    
    return {"order_id": order_id, "status": "cancelled"}


# ═══════════════════════════════════════════════════════════════════
# ACTIVITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/activities/search")
async def search_activities(lat: float, lng: float, radius: int = 5):
    data = await amadeus_get("/v1/shopping/activities", {"latitude": lat, "longitude": lng, "radius": radius})
    return {"count": len(data), "activities": data}


@app.get("/activities/city/{city_code}")
async def get_activities_by_city(city_code: str, radius: int = 10):
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
    data = await amadeus_get("/v1/reference-data/locations", {"keyword": keyword, "subType": "CITY,AIRPORT"})
    return {"count": len(data), "locations": data}


@app.get("/airlines/{airline_code}/checkin")
async def get_checkin_link(airline_code: str):
    data = await amadeus_get("/v2/reference-data/urls/checkin-links", {"airlineCode": airline_code.upper()})
    return {"airline": airline_code.upper(), "links": data}


@app.get("/airlines/{airline_code}")
async def get_airline_info(airline_code: str):
    data = await amadeus_get("/v1/reference-data/airlines", {"airlineCodes": airline_code.upper()})
    if not data:
        raise HTTPException(status_code=404, detail="Airline not found")
    return data[0]


@app.get("/recommendations")
async def get_recommendations(cities: str, country: str = "US"):
    data = await amadeus_get("/v1/reference-data/recommended-locations", 
                             {"cityCodes": cities.upper(), "travelerCountryCode": country.upper()})
    return {"count": len(data), "recommendations": data}


# ═══════════════════════════════════════════════════════════════════
# DATABASE STATS
# ═══════════════════════════════════════════════════════════════════

@app.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get database statistics"""
    users = await db.execute(select(func.count()).select_from(User))
    conversations = await db.execute(select(func.count()).select_from(Conversation))
    bookings = await db.execute(select(func.count()).select_from(Booking))
    policies = await db.execute(select(func.count()).select_from(Policy))
    
    return {
        "users": users.scalar(),
        "conversations": conversations.scalar(),
        "bookings": bookings.scalar(),
        "policies": policies.scalar()
    }


# --- AGENT CHAT ENDPOINT ---

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: str

# Global instance initialized via build_graph from orchestrator
agent_app = build_graph()

@app.post("/chat")
async def chat_with_agent(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    # 1. Verify User and Conversation
    # 2. Load Message History
    past_messages = [] 
    current_message = HumanMessage(content=request.message)
    
    # 3. State Preparation
    initial_state = {
        "messages": past_messages + [current_message],
        "customer_id": request.user_id,
        "next_agent": None
    }
    
    # 4. Run Graph
    # 'ainvoke' works asynchronously, fully compatible with FastAPI
    result = await agent_app.ainvoke(initial_state)
    
    # 5. Get Results
    last_message = result["messages"][-1]
    
    # 6. Save to Database (Can be done in background)
    
    return {
        "response": last_message.content,
        "intent": result.get("intent"),
        "urgency": result.get("urgency"),
        "context": result.get("booking_context")
    }

# ═══════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)