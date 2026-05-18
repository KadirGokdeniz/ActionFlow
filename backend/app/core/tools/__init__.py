from app.core.tools.mcp_client import mcp_client, MCPClient
from app.core.tools.search import search_flights, search_hotels, get_hotel_offers, search_policies
from app.core.tools.booking import (
    create_booking, get_user_bookings, get_booking_details,
    cancel_booking, modify_booking, booking_tools,
)
from app.core.tools.location import (
    resolve_location, search_cities_by_country, validate_route, location_tools,
)

info_tools = [search_policies]
action_tools = [
    search_flights, search_hotels, get_hotel_offers,
    create_booking, get_user_bookings, get_booking_details,
    cancel_booking, modify_booking,
]
all_tools = info_tools + action_tools + location_tools

__all__ = [
    "mcp_client", "MCPClient",
    "info_tools", "action_tools", "location_tools", "booking_tools", "all_tools",
    "search_flights", "search_hotels", "get_hotel_offers", "search_policies",
    "create_booking", "get_user_bookings", "get_booking_details",
    "cancel_booking", "modify_booking",
    "resolve_location", "search_cities_by_country", "validate_route",
]
