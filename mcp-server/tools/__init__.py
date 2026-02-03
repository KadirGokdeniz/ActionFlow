"""
ActionFlow MCP Tools Registry
Tüm tool tanımlarını ve fonksiyonlarını merkezi olarak yönetir.

Tools:
- Flights: search_flights
- Hotels: search_hotels, get_hotel_offers
- Bookings: create_booking, get_user_bookings, cancel_booking, get_booking_details, modify_booking
- Policies: search_policies
"""

from typing import Dict, Callable, List

# Import tool definitions and functions
from tools.flights import (
    TOOL_DEFINITION as FLIGHT_SEARCH_DEF,
    search_flights
)

from tools.hotels import (
    SEARCH_HOTELS_DEFINITION,
    GET_HOTEL_OFFERS_DEFINITION,
    search_hotels,
    get_hotel_offers
)

from tools.bookings import (
    CREATE_BOOKING_DEFINITION,
    GET_USER_BOOKINGS_DEFINITION,
    CANCEL_BOOKING_DEFINITION,
    GET_BOOKING_DETAILS_DEFINITION,
    MODIFY_BOOKING_DEFINITION,
    create_booking,
    get_user_bookings,
    cancel_booking,
    get_booking_details,
    modify_booking
)

from tools.policies import (
    TOOL_DEFINITION as POLICY_SEARCH_DEF,
    search_policies
)


# ═══════════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ═══════════════════════════════════════════════════════════════════

# All tool definitions (MCP schema format)
TOOLS: List[Dict] = [
    # Flight tools
    FLIGHT_SEARCH_DEF,
    
    # Hotel tools
    SEARCH_HOTELS_DEFINITION,
    GET_HOTEL_OFFERS_DEFINITION,
    
    # Booking tools
    CREATE_BOOKING_DEFINITION,
    GET_USER_BOOKINGS_DEFINITION,
    CANCEL_BOOKING_DEFINITION,
    GET_BOOKING_DETAILS_DEFINITION,
    MODIFY_BOOKING_DEFINITION,
    
    # Policy tools
    POLICY_SEARCH_DEF,
]

# Tool name → function mapping
TOOL_FUNCTIONS: Dict[str, Callable] = {
    # Flights
    "search_flights": search_flights,
    
    # Hotels
    "search_hotels": search_hotels,
    "get_hotel_offers": get_hotel_offers,
    
    # Bookings
    "create_booking": create_booking,
    "get_user_bookings": get_user_bookings,
    "cancel_booking": cancel_booking,
    "get_booking_details": get_booking_details,
    "modify_booking": modify_booking,
    
    # Policies
    "search_policies": search_policies,
}


def tool_exists(name: str) -> bool:
    """Tool var mı kontrol et"""
    return name in TOOL_FUNCTIONS


def get_tool_definition(name: str) -> Dict:
    """Tool tanımını getir"""
    for tool in TOOLS:
        if tool["name"] == name:
            return tool
    return None


def list_tool_names() -> List[str]:
    """Tüm tool isimlerini listele"""
    return list(TOOL_FUNCTIONS.keys())


# ═══════════════════════════════════════════════════════════════════
# TOOL CATEGORIES (for organization)
# ═══════════════════════════════════════════════════════════════════

TOOL_CATEGORIES = {
    "search": ["search_flights", "search_hotels", "get_hotel_offers", "search_policies"],
    "booking": ["create_booking", "get_user_bookings", "get_booking_details"],
    "management": ["cancel_booking", "modify_booking"],
}


def get_tools_by_category(category: str) -> List[str]:
    """Kategoriye göre tool'ları getir"""
    return TOOL_CATEGORIES.get(category, [])


# ═══════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════

__all__ = [
    "TOOLS",
    "TOOL_FUNCTIONS",
    "tool_exists",
    "get_tool_definition",
    "list_tool_names",
    "TOOL_CATEGORIES",
    "get_tools_by_category",
]