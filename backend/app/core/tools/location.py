"""
ActionFlow - Location Resolution Tools
Şehir adı → IATA kodu çözümleme (Self-contained, no external dependencies)
"""

import json
import logging
from typing import Optional, List
from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger("ActionFlow-Location")


# ═══════════════════════════════════════════════════════════════════
# AIRPORT DATABASE (Built-in)
# ═══════════════════════════════════════════════════════════════════

AIRPORTS = {
    # TÜRKİYE
    "istanbul": {"iata": "IST", "city": "Istanbul", "country": "Turkey", "aliases": ["ist", "istanbul"]},
    "ankara": {"iata": "ESB", "city": "Ankara", "country": "Turkey", "aliases": ["ankara", "esenboga"]},
    "izmir": {"iata": "ADB", "city": "Izmir", "country": "Turkey", "aliases": ["izmir", "adnan menderes"]},
    "antalya": {"iata": "AYT", "city": "Antalya", "country": "Turkey", "aliases": ["antalya"]},
    "bodrum": {"iata": "BJV", "city": "Bodrum", "country": "Turkey", "aliases": ["bodrum", "milas"]},
    "dalaman": {"iata": "DLM", "city": "Dalaman", "country": "Turkey", "aliases": ["dalaman", "fethiye"]},
    "trabzon": {"iata": "TZX", "city": "Trabzon", "country": "Turkey", "aliases": ["trabzon"]},
    "adana": {"iata": "ADA", "city": "Adana", "country": "Turkey", "aliases": ["adana"]},
    "gaziantep": {"iata": "GZT", "city": "Gaziantep", "country": "Turkey", "aliases": ["gaziantep", "antep"]},
    "sabiha": {"iata": "SAW", "city": "Istanbul", "country": "Turkey", "aliases": ["sabiha", "sabiha gokcen"]},
    
    # AVRUPA
    "paris": {"iata": "CDG", "city": "Paris", "country": "France", "aliases": ["paris", "cdg"]},
    "london": {"iata": "LHR", "city": "London", "country": "United Kingdom", "aliases": ["london", "londra", "heathrow"]},
    "amsterdam": {"iata": "AMS", "city": "Amsterdam", "country": "Netherlands", "aliases": ["amsterdam", "schiphol"]},
    "frankfurt": {"iata": "FRA", "city": "Frankfurt", "country": "Germany", "aliases": ["frankfurt"]},
    "munich": {"iata": "MUC", "city": "Munich", "country": "Germany", "aliases": ["munich", "munih"]},
    "berlin": {"iata": "BER", "city": "Berlin", "country": "Germany", "aliases": ["berlin"]},
    "rome": {"iata": "FCO", "city": "Rome", "country": "Italy", "aliases": ["rome", "roma"]},
    "milan": {"iata": "MXP", "city": "Milan", "country": "Italy", "aliases": ["milan", "milano"]},
    "barcelona": {"iata": "BCN", "city": "Barcelona", "country": "Spain", "aliases": ["barcelona", "barselona"]},
    "madrid": {"iata": "MAD", "city": "Madrid", "country": "Spain", "aliases": ["madrid"]},
    "vienna": {"iata": "VIE", "city": "Vienna", "country": "Austria", "aliases": ["vienna", "viyana"]},
    "zurich": {"iata": "ZRH", "city": "Zurich", "country": "Switzerland", "aliases": ["zurich", "zurih"]},
    "brussels": {"iata": "BRU", "city": "Brussels", "country": "Belgium", "aliases": ["brussels", "bruksel"]},
    "prague": {"iata": "PRG", "city": "Prague", "country": "Czech Republic", "aliases": ["prague", "prag"]},
    "budapest": {"iata": "BUD", "city": "Budapest", "country": "Hungary", "aliases": ["budapest", "budapeste"]},
    "warsaw": {"iata": "WAW", "city": "Warsaw", "country": "Poland", "aliases": ["warsaw", "varsova"]},
    "athens": {"iata": "ATH", "city": "Athens", "country": "Greece", "aliases": ["athens", "atina"]},
    "lisbon": {"iata": "LIS", "city": "Lisbon", "country": "Portugal", "aliases": ["lisbon", "lizbon"]},
    "dublin": {"iata": "DUB", "city": "Dublin", "country": "Ireland", "aliases": ["dublin"]},
    "copenhagen": {"iata": "CPH", "city": "Copenhagen", "country": "Denmark", "aliases": ["copenhagen", "kopenhag"]},
    "stockholm": {"iata": "ARN", "city": "Stockholm", "country": "Sweden", "aliases": ["stockholm"]},
    "oslo": {"iata": "OSL", "city": "Oslo", "country": "Norway", "aliases": ["oslo"]},
    "helsinki": {"iata": "HEL", "city": "Helsinki", "country": "Finland", "aliases": ["helsinki"]},
    
    # AMERİKA
    "new york": {"iata": "JFK", "city": "New York", "country": "USA", "aliases": ["new york", "nyc", "jfk"]},
    "los angeles": {"iata": "LAX", "city": "Los Angeles", "country": "USA", "aliases": ["los angeles", "la", "lax"]},
    "chicago": {"iata": "ORD", "city": "Chicago", "country": "USA", "aliases": ["chicago", "sikago"]},
    "miami": {"iata": "MIA", "city": "Miami", "country": "USA", "aliases": ["miami"]},
    "san francisco": {"iata": "SFO", "city": "San Francisco", "country": "USA", "aliases": ["san francisco", "sf"]},
    "washington": {"iata": "IAD", "city": "Washington", "country": "USA", "aliases": ["washington", "dc"]},
    "boston": {"iata": "BOS", "city": "Boston", "country": "USA", "aliases": ["boston"]},
    "toronto": {"iata": "YYZ", "city": "Toronto", "country": "Canada", "aliases": ["toronto"]},
    "montreal": {"iata": "YUL", "city": "Montreal", "country": "Canada", "aliases": ["montreal"]},
    
    # ASYA & ORTA DOĞU
    "tokyo": {"iata": "NRT", "city": "Tokyo", "country": "Japan", "aliases": ["tokyo", "narita"]},
    "dubai": {"iata": "DXB", "city": "Dubai", "country": "UAE", "aliases": ["dubai", "dxb"]},
    "singapore": {"iata": "SIN", "city": "Singapore", "country": "Singapore", "aliases": ["singapore", "singapur"]},
    "hong kong": {"iata": "HKG", "city": "Hong Kong", "country": "Hong Kong", "aliases": ["hong kong", "hongkong"]},
    "bangkok": {"iata": "BKK", "city": "Bangkok", "country": "Thailand", "aliases": ["bangkok"]},
    "seoul": {"iata": "ICN", "city": "Seoul", "country": "South Korea", "aliases": ["seoul", "seul"]},
    "beijing": {"iata": "PEK", "city": "Beijing", "country": "China", "aliases": ["beijing", "pekin"]},
    "shanghai": {"iata": "PVG", "city": "Shanghai", "country": "China", "aliases": ["shanghai"]},
    "delhi": {"iata": "DEL", "city": "Delhi", "country": "India", "aliases": ["delhi", "new delhi"]},
    "mumbai": {"iata": "BOM", "city": "Mumbai", "country": "India", "aliases": ["mumbai", "bombay"]},
    "doha": {"iata": "DOH", "city": "Doha", "country": "Qatar", "aliases": ["doha", "katar"]},
    "tel aviv": {"iata": "TLV", "city": "Tel Aviv", "country": "Israel", "aliases": ["tel aviv", "telaviv"]},
    "cairo": {"iata": "CAI", "city": "Cairo", "country": "Egypt", "aliases": ["cairo", "kahire"]},
    
    # OKYANUSYA
    "sydney": {"iata": "SYD", "city": "Sydney", "country": "Australia", "aliases": ["sydney"]},
    "melbourne": {"iata": "MEL", "city": "Melbourne", "country": "Australia", "aliases": ["melbourne"]},
}

# IATA → City reverse lookup
IATA_TO_CITY = {info["iata"]: key for key, info in AIRPORTS.items()}


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def find_airport(query: str) -> Optional[dict]:
    """Find airport by city name, alias, or IATA code"""
    query_lower = query.lower().strip()
    
    # Direct IATA code?
    if len(query_lower) == 3 and query_lower.upper() in IATA_TO_CITY:
        city_key = IATA_TO_CITY[query_lower.upper()]
        return AIRPORTS[city_key]
    
    # Exact city name match
    if query_lower in AIRPORTS:
        return AIRPORTS[query_lower]
    
    # Alias match
    for city_key, info in AIRPORTS.items():
        if query_lower in info.get("aliases", []):
            return info
    
    # Partial match
    for city_key, info in AIRPORTS.items():
        if query_lower in city_key:
            return info
        for alias in info.get("aliases", []):
            if query_lower in alias:
                return info
    
    return None


def get_cities_by_country(country: str) -> List[dict]:
    """List cities by country"""
    country_lower = country.lower()
    results = []
    
    for city_key, info in AIRPORTS.items():
        if info["country"].lower() == country_lower:
            results.append({
                "city": info["city"],
                "iata": info["iata"],
                "country": info["country"]
            })
    
    return results


# ═══════════════════════════════════════════════════════════════════
# TOOL SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class ResolveLocationArgs(BaseModel):
    query: str = Field(description="City name, alias, or IATA code to resolve")


class SearchCitiesArgs(BaseModel):
    country: str = Field(description="Country name to search cities in")


class ValidateRouteArgs(BaseModel):
    origin: str = Field(description="Origin city or IATA code")
    destination: str = Field(description="Destination city or IATA code")


# ═══════════════════════════════════════════════════════════════════
# LANGCHAIN TOOLS
# ═══════════════════════════════════════════════════════════════════

@tool(args_schema=ResolveLocationArgs)
def resolve_location(query: str) -> str:
    """
    Resolve a city name to its IATA airport code.
    Use this before searching flights to get the correct airport code.
    
    Examples:
        "Paris" → CDG
        "Istanbul" → IST
    """
    logger.info(f"🔍 Resolving location: {query}")
    
    result = find_airport(query)
    
    if result:
        return json.dumps({
            "success": True,
            "iata": result["iata"],
            "city": result["city"],
            "country": result["country"]
        })
    else:
        return json.dumps({
            "success": False,
            "error": f"Could not find airport for: {query}",
            "suggestion": "Try a major city name or IATA code"
        })


@tool(args_schema=SearchCitiesArgs)
def search_cities_by_country(country: str) -> str:
    """
    List all available cities/airports in a country.
    
    Example: "Turkey" → Istanbul, Ankara, Izmir, etc.
    """
    logger.info(f"🔍 Searching cities in: {country}")
    
    cities = get_cities_by_country(country)
    
    if cities:
        return json.dumps({
            "success": True,
            "country": country,
            "count": len(cities),
            "cities": cities
        })
    else:
        return json.dumps({
            "success": False,
            "error": f"No cities found for country: {country}"
        })


@tool(args_schema=ValidateRouteArgs)
def validate_route(origin: str, destination: str) -> str:
    """
    Validate both origin and destination and return their IATA codes.
    Use this to validate a complete route before searching flights.
    """
    logger.info(f"🔍 Validating route: {origin} → {destination}")
    
    origin_result = find_airport(origin)
    dest_result = find_airport(destination)
    
    if origin_result and dest_result:
        return json.dumps({
            "success": True,
            "origin": {
                "iata": origin_result["iata"],
                "city": origin_result["city"],
                "country": origin_result["country"]
            },
            "destination": {
                "iata": dest_result["iata"],
                "city": dest_result["city"],
                "country": dest_result["country"]
            }
        })
    else:
        errors = []
        if not origin_result:
            errors.append(f"Could not find origin: {origin}")
        if not dest_result:
            errors.append(f"Could not find destination: {destination}")
        
        return json.dumps({
            "success": False,
            "errors": errors
        })


# ═══════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════

location_tools = [resolve_location, search_cities_by_country, validate_route]

__all__ = [
    "resolve_location",
    "search_cities_by_country",
    "validate_route",
    "location_tools",
    "find_airport",
    "AIRPORTS"
]