from datetime import datetime
from typing import List, Tuple
from app.core.schemas import (
    TravelContext, 
    REQUIRED_FIELDS_CORE, 
    OPTIONAL_FIELDS_IMPORTANT, 
    OPTIONAL_FIELDS_EXTRA
)

def get_system_context() -> str:
    """Returns current time context"""
    now = datetime.now()
    return f"""
CURRENT DATE: {now.strftime('%Y-%m-%d')}
CURRENT TIME: {now.strftime('%H:%M')}
CURRENT YEAR: {now.year}
TODAY: {now.strftime('%A')}

All relative dates (tomorrow, next week) must be converted to actual dates in {now.year}.
"""

def create_empty_travel_context() -> TravelContext:
    """Creates an empty travel context"""
    return TravelContext(
        budget_currency="EUR",
        collected_fields=[],
        plan_approved=False,
        booking_ids=[]
    )

def check_required_fields(travel_context: TravelContext) -> Tuple[bool, List[str], List[str]]:
    """
    Check if required fields are collected.
    
    Returns:
        (is_complete, missing_required, missing_optional)
    """
    collected = travel_context.get("collected_fields", [])
    
    # Zorunlu alanları kontrol et
    missing_required = [f for f in REQUIRED_FIELDS_CORE if f not in collected]
    
    # Önemli opsiyonel alanları kontrol et
    missing_optional = [f for f in OPTIONAL_FIELDS_IMPORTANT if f not in collected]
    
    # Zorunlu alanlar tamamsa, hazırız
    is_complete = len(missing_required) == 0
    
    return is_complete, missing_required, missing_optional

def format_collected_info(travel_context: TravelContext) -> str:
    """Format collected travel info for display"""
    parts = []
    
    if travel_context.get("origin"):
        parts.append(f"🛫 From: {travel_context['origin']}")
    if travel_context.get("destination"):
        parts.append(f"🛬 To: {travel_context['destination']}")
    if travel_context.get("departure_date"):
        parts.append(f"📅 Departure: {travel_context['departure_date']}")
    if travel_context.get("return_date"):
        parts.append(f"📅 Return: {travel_context['return_date']}")
    if travel_context.get("travelers"):
        parts.append(f"👥 Travelers: {travel_context['travelers']}")
    if travel_context.get("budget_max"):
        parts.append(f"💰 Budget: max {travel_context['budget_max']} {travel_context.get('budget_currency', 'EUR')}/person")
    if travel_context.get("motivation"):
        parts.append(f"🎯 Motivation: {travel_context['motivation']}")
    if travel_context.get("transportation_pref"):
        parts.append(f"🚆 Transportation: {travel_context['transportation_pref']}")
    if travel_context.get("activity_pref"):
        parts.append(f"🏛️ Activities: {travel_context['activity_pref']}")
    if travel_context.get("dietary_pref"):
        parts.append(f"🍽️ Dietary: {travel_context['dietary_pref']}")
    
    return "\n".join(parts) if parts else "No information collected yet."

def create_plan_summary(travel_context: TravelContext) -> str:
    """Create a travel plan summary from collected info"""
    parts = []
    
    origin = travel_context.get("origin", "IST")
    dest = travel_context.get("destination", "?")
    dep_date = travel_context.get("departure_date", "?")
    ret_date = travel_context.get("return_date", "?")
    travelers = travel_context.get("travelers", 1)
    budget = travel_context.get("budget_max")
    
    parts.append(f"🛫 {origin} → {dest}")
    parts.append(f"📅 {dep_date} - {ret_date}")
    parts.append(f"👥 {travelers} traveler(s)")
    
    if budget:
        currency = travel_context.get("budget_currency", "EUR")
        parts.append(f"💰 Max {budget} {currency}/person")
    
    if travel_context.get("motivation"):
        parts.append(f"🎯 Purpose: {travel_context['motivation']}")
    
    return "\n".join(parts)
