"""
ActionFlow AI - LangChain Tools
MCP Server üzerinden çağrılan tool tanımları

Tools:
- Search: search_flights, search_hotels, get_hotel_offers, search_policies
- Booking: create_booking, get_user_bookings, get_booking_details
- Management: cancel_booking, modify_booking
- Location: resolve_location, search_cities_by_country, validate_route
"""

import os
import json
import uuid
import logging
import httpx
from typing import List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.core.tools.location import (
    resolve_location,
    search_cities_by_country,
    validate_route,
    location_tools
)


logger = logging.getLogger("ActionFlow-Tools")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:3000")


# ═══════════════════════════════════════════════════════════════════
# MCP CLIENT
# ═══════════════════════════════════════════════════════════════════

class MCPClient:
    """MCP Server communication client"""
    
    def __init__(self, base_url: str = MCP_SERVER_URL):
        self.base_url = base_url
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0
            )
        return self._http_client
    
    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
    
    async def list_tools(self) -> List[dict]:
        """List available MCP tools"""
        client = await self._get_client()
        response = await client.post("/message", json={
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": str(uuid.uuid4())
        })
        data = response.json()
        return data.get("result", {}).get("tools", [])
    
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        client = await self._get_client()
        
        logger.info(f"🔧 MCP Call: {tool_name} with {arguments}")
        
        response = await client.post("/message", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": str(uuid.uuid4())
        })
        
        data = response.json()
        
        if "error" in data:
            logger.error(f"MCP Error: {data['error']}")
            return {"success": False, "error": data["error"]["message"]}
        
        content = data.get("result", {}).get("content", [])
        if content and content[0].get("type") == "text":
            try:
                return json.loads(content[0]["text"])
            except json.JSONDecodeError:
                return {"success": True, "text": content[0]["text"]}
        
        return {"success": False, "error": "Empty response"}


mcp_client = MCPClient()


# ═══════════════════════════════════════════════════════════════════
# TOOL ARGUMENT SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class SearchFlightsArgs(BaseModel):
    origin: str = Field(description="Origin IATA code (e.g., IST)")
    destination: str = Field(description="Destination IATA code (e.g., AMS)")
    date: str = Field(description="Flight date (YYYY-MM-DD)")
    adults: int = Field(default=1, description="Number of passengers")
    return_date: Optional[str] = Field(default=None, description="Return date (optional)")


class SearchHotelsArgs(BaseModel):
    city_code: str = Field(description="IATA city code (e.g., PAR)")
    radius: int = Field(default=5, description="Search radius in km")


class GetHotelOffersArgs(BaseModel):
    hotel_ids: List[str] = Field(description="List of hotel IDs")
    check_in: str = Field(description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(description="Check-out date (YYYY-MM-DD)")
    adults: int = Field(default=1, description="Number of adults")


class CreateBookingArgs(BaseModel):
    """Rezervasyon oluşturma argümanları"""
    booking_type: str = Field(description="Booking type: flight, hotel, or package")
    passenger_first_name: str = Field(description="Passenger first name")
    passenger_last_name: str = Field(description="Passenger last name")
    passenger_email: str = Field(description="Contact email address")
    passenger_phone: Optional[str] = Field(default=None, description="Contact phone number")
    flight_offer_id: Optional[str] = Field(default=None, description="Flight offer ID (for flight/package)")
    hotel_offer_id: Optional[str] = Field(default=None, description="Hotel offer ID (for hotel/package)")
    check_in: Optional[str] = Field(default=None, description="Check-in date (YYYY-MM-DD)")
    check_out: Optional[str] = Field(default=None, description="Check-out date (YYYY-MM-DD)")
    guests: int = Field(default=1, description="Number of guests")


class GetUserBookingsArgs(BaseModel):
    user_id: str = Field(description="User ID")
    status: str = Field(default="all", description="Status filter")
    booking_type: str = Field(default="all", description="Type filter")


class CancelBookingArgs(BaseModel):
    booking_id: str = Field(description="Booking ID")
    reason: Optional[str] = Field(default=None, description="Cancellation reason")


class GetBookingDetailsArgs(BaseModel):
    booking_id: str = Field(description="Booking ID")


class ModifyBookingArgs(BaseModel):
    """Rezervasyon değiştirme argümanları"""
    booking_id: str = Field(description="Booking ID to modify")
    new_check_in: Optional[str] = Field(default=None, description="New check-in/departure date (YYYY-MM-DD)")
    new_check_out: Optional[str] = Field(default=None, description="New check-out/return date (YYYY-MM-DD)")


class SearchPoliciesArgs(BaseModel):
    query: str = Field(description="Search query")
    category: Optional[str] = Field(default=None, description="Category filter")
    provider: Optional[str] = Field(default=None, description="Provider filter")


# ═══════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS - SEARCH
# ═══════════════════════════════════════════════════════════════════

@tool(args_schema=SearchFlightsArgs)
async def search_flights(
    origin: str,
    destination: str,
    date: str,
    adults: int = 1,
    return_date: Optional[str] = None
) -> str:
    """Search flights between two cities. Use IATA codes for origin and destination."""
    result = await mcp_client.call_tool("search_flights", {
        "origin": origin,
        "destination": destination,
        "date": date,
        "adults": adults,
        "return_date": return_date
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool(args_schema=SearchHotelsArgs)
async def search_hotels(city_code: str, radius: int = 5) -> str:
    """Search hotels in a city. Use IATA city code (e.g., PAR for Paris)."""
    result = await mcp_client.call_tool("search_hotels", {
        "city_code": city_code,
        "radius": radius
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool(args_schema=GetHotelOffersArgs)
async def get_hotel_offers(
    hotel_ids: List[str],
    check_in: str,
    check_out: str,
    adults: int = 1
) -> str:
    """Get hotel prices and availability for specific hotels."""
    result = await mcp_client.call_tool("get_hotel_offers", {
        "hotel_ids": hotel_ids,
        "check_in": check_in,
        "check_out": check_out,
        "adults": adults
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool(args_schema=SearchPoliciesArgs)
async def search_policies(
    query: str,
    category: Optional[str] = None,
    provider: Optional[str] = None
) -> str:
    """Search travel policies: cancellation rules, refund conditions, baggage allowances."""
    result = await mcp_client.call_tool("search_policies", {
        "query": query,
        "category": category,
        "provider": provider
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS - BOOKING
# ═══════════════════════════════════════════════════════════════════

@tool(args_schema=CreateBookingArgs)
async def create_booking(
    booking_type: str,
    passenger_first_name: str,
    passenger_last_name: str,
    passenger_email: str,
    passenger_phone: Optional[str] = None,
    flight_offer_id: Optional[str] = None,
    hotel_offer_id: Optional[str] = None,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
    guests: int = 1
) -> str:
    """
    Create a new booking (flight, hotel, or package).
    
    IMPORTANT: Only call this AFTER getting user confirmation!
    This creates a REAL booking and sends confirmation email.
    
    For package bookings (recommended), provide both flight_offer_id and hotel_offer_id.
    """
    result = await mcp_client.call_tool("create_booking", {
        "booking_type": booking_type,
        "passenger_first_name": passenger_first_name,
        "passenger_last_name": passenger_last_name,
        "passenger_email": passenger_email,
        "passenger_phone": passenger_phone,
        "flight_offer_id": flight_offer_id,
        "hotel_offer_id": hotel_offer_id,
        "check_in": check_in,
        "check_out": check_out,
        "guests": guests
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool(args_schema=GetUserBookingsArgs)
async def get_user_bookings(
    user_id: str,
    status: str = "all",
    booking_type: str = "all"
) -> str:
    """List user's bookings. Can filter by status and booking type."""
    result = await mcp_client.call_tool("get_user_bookings", {
        "user_id": user_id,
        "status": status,
        "booking_type": booking_type
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool(args_schema=GetBookingDetailsArgs)
async def get_booking_details(booking_id: str) -> str:
    """Get detailed information about a specific booking."""
    result = await mcp_client.call_tool("get_booking_details", {
        "booking_id": booking_id
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS - MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@tool(args_schema=CancelBookingArgs)
async def cancel_booking(booking_id: str, reason: Optional[str] = None) -> str:
    """
    Cancel a booking.
    
    WARNING: This action CANNOT be undone!
    Only call after getting explicit user confirmation.
    Refund will be processed according to cancellation policy.
    """
    result = await mcp_client.call_tool("cancel_booking", {
        "booking_id": booking_id,
        "reason": reason
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool(args_schema=ModifyBookingArgs)
async def modify_booking(
    booking_id: str,
    new_check_in: Optional[str] = None,
    new_check_out: Optional[str] = None
) -> str:
    """
    Modify an existing booking (change dates).
    
    Modification fee may apply. Inform user before proceeding.
    """
    result = await mcp_client.call_tool("modify_booking", {
        "booking_id": booking_id,
        "new_check_in": new_check_in,
        "new_check_out": new_check_out
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════════
# TOOL COLLECTIONS
# ═══════════════════════════════════════════════════════════════════

# Info tools - for policy questions (Info Agent uses these)
info_tools = [search_policies]

# Action tools - for searches and bookings (Action Agent uses these)
action_tools = [
    # Search
    search_flights,
    search_hotels,
    get_hotel_offers,
    # Booking
    create_booking,
    get_user_bookings,
    get_booking_details,
    # Management
    cancel_booking,
    modify_booking
]

# Location tools (imported from location module)
location_tools = location_tools

# All tools combined
all_tools = info_tools + action_tools + location_tools


# ═══════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════

__all__ = [
    # Client
    "mcp_client",
    "MCPClient",
    
    # Tool collections
    "info_tools",
    "action_tools", 
    "location_tools",
    "all_tools",
    
    # Individual tools
    "search_flights",
    "search_hotels",
    "get_hotel_offers",
    "search_policies",
    "create_booking",
    "get_user_bookings",
    "get_booking_details",
    "cancel_booking",
    "modify_booking",
    "resolve_location",
    "search_cities_by_country",
    "validate_route",
]