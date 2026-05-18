import json
from typing import List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from app.core.tools.mcp_client import mcp_client


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


class SearchPoliciesArgs(BaseModel):
    query: str = Field(description="Search query")
    category: Optional[str] = Field(default=None, description="Category filter")
    provider: Optional[str] = Field(default=None, description="Provider filter")


@tool(args_schema=SearchFlightsArgs)
async def search_flights(origin: str, destination: str, date: str,
                         adults: int = 1, return_date: Optional[str] = None) -> str:
    """Search flights between two cities. Use IATA codes for origin and destination."""
    return json.dumps(await mcp_client.call_tool("search_flights", {
        "origin": origin, "destination": destination, "date": date,
        "adults": adults, "return_date": return_date
    }), ensure_ascii=False, indent=2)


@tool(args_schema=SearchHotelsArgs)
async def search_hotels(city_code: str, radius: int = 5) -> str:
    """Search hotels in a city. Use IATA city code (e.g., PAR for Paris)."""
    return json.dumps(await mcp_client.call_tool("search_hotels", {
        "city_code": city_code, "radius": radius
    }), ensure_ascii=False, indent=2)


@tool(args_schema=GetHotelOffersArgs)
async def get_hotel_offers(hotel_ids: List[str], check_in: str,
                           check_out: str, adults: int = 1) -> str:
    """Get hotel prices and availability for specific hotels."""
    return json.dumps(await mcp_client.call_tool("get_hotel_offers", {
        "hotel_ids": hotel_ids, "check_in": check_in,
        "check_out": check_out, "adults": adults
    }), ensure_ascii=False, indent=2)


@tool(args_schema=SearchPoliciesArgs)
async def search_policies(query: str, category: Optional[str] = None,
                          provider: Optional[str] = None) -> str:
    """Search travel policies: cancellation rules, refund conditions, baggage allowances."""
    return json.dumps(await mcp_client.call_tool("search_policies", {
        "query": query, "category": category, "provider": provider
    }), ensure_ascii=False, indent=2)
