import json
from typing import List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from app.core.tools.mcp_client import mcp_client


class CreateBookingArgs(BaseModel):
    booking_type: str = Field(description="Booking type: flight, hotel, or package")
    passenger_first_name: str = Field(description="Passenger first name")
    passenger_last_name: str = Field(description="Passenger last name")
    passenger_email: str = Field(description="Contact email address")
    passenger_phone: Optional[str] = Field(default=None, description="Contact phone number")
    flight_offer_id: Optional[str] = Field(default=None, description="Flight offer ID")
    hotel_offer_id: Optional[str] = Field(default=None, description="Hotel offer ID")
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
    booking_id: str = Field(description="Booking ID to modify")
    new_check_in: Optional[str] = Field(default=None, description="New check-in/departure date")
    new_check_out: Optional[str] = Field(default=None, description="New check-out/return date")


@tool(args_schema=CreateBookingArgs)
async def create_booking(booking_type: str, passenger_first_name: str,
                         passenger_last_name: str, passenger_email: str,
                         passenger_phone: Optional[str] = None,
                         flight_offer_id: Optional[str] = None,
                         hotel_offer_id: Optional[str] = None,
                         check_in: Optional[str] = None,
                         check_out: Optional[str] = None, guests: int = 1) -> str:
    """Create a new booking (flight, hotel, or package). Only call AFTER user confirmation."""
    return json.dumps(await mcp_client.call_tool("create_booking", {
        "booking_type": booking_type, "passenger_first_name": passenger_first_name,
        "passenger_last_name": passenger_last_name, "passenger_email": passenger_email,
        "passenger_phone": passenger_phone, "flight_offer_id": flight_offer_id,
        "hotel_offer_id": hotel_offer_id, "check_in": check_in,
        "check_out": check_out, "guests": guests
    }), ensure_ascii=False, indent=2)


@tool(args_schema=GetUserBookingsArgs)
async def get_user_bookings(user_id: str, status: str = "all",
                            booking_type: str = "all") -> str:
    """List user bookings. Can filter by status and booking type."""
    return json.dumps(await mcp_client.call_tool("get_user_bookings", {
        "user_id": user_id, "status": status, "booking_type": booking_type
    }), ensure_ascii=False, indent=2)


@tool(args_schema=GetBookingDetailsArgs)
async def get_booking_details(booking_id: str) -> str:
    """Get detailed information about a specific booking."""
    return json.dumps(await mcp_client.call_tool("get_booking_details", {
        "booking_id": booking_id
    }), ensure_ascii=False, indent=2)


@tool(args_schema=CancelBookingArgs)
async def cancel_booking(booking_id: str, reason: Optional[str] = None) -> str:
    """Cancel a booking. WARNING: Cannot be undone. Only call after explicit user confirmation."""
    return json.dumps(await mcp_client.call_tool("cancel_booking", {
        "booking_id": booking_id, "reason": reason
    }), ensure_ascii=False, indent=2)


@tool(args_schema=ModifyBookingArgs)
async def modify_booking(booking_id: str, new_check_in: Optional[str] = None,
                         new_check_out: Optional[str] = None) -> str:
    """Modify an existing booking. Modification fee may apply."""
    return json.dumps(await mcp_client.call_tool("modify_booking", {
        "booking_id": booking_id, "new_check_in": new_check_in,
        "new_check_out": new_check_out
    }), ensure_ascii=False, indent=2)


booking_tools = [
    create_booking, get_user_bookings, get_booking_details,
    cancel_booking, modify_booking,
]
