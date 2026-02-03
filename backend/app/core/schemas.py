from enum import Enum
from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
import operator  # ← EKLE!

class ConversationState(str, Enum):
    """Simplified conversation states"""
    IDLE = "idle"                      # Initial state
    SHARPENING = "sharpening"          # Collecting travel info (Sharpener owns this)
    READY_FOR_ACTION = "ready"         # Plan complete, ready for Action
    ACTION = "action"                  # Executing searches/bookings
    INFO = "info"                      # Answering policy questions
    COMPLETED = "completed"            # Task done
    ESCALATION = "escalation"          # Human handoff

class TravelContext(TypedDict, total=False):
    """Travel planning context - collected information"""
    # Basic info
    origin: str                        # IATA code
    destination: str                   # IATA code  
    departure_date: str                # YYYY-MM-DD
    return_date: Optional[str]         # YYYY-MM-DD (optional for one-way)
    travelers: int = 1                 # Number of passengers
    
    # Preferences
    budget_max: Optional[float]        # Max budget per person
    budget_currency: str               # Currency (default EUR)
    trip_type: Optional[str]           # LEISURE | BUSINESS
    accommodation_pref: Optional[str]  # HOTEL | HOSTEL | APARTMENT
    travel_class: Optional[str]        # ECONOMY | BUSINESS | FIRST
    
    # Expanded Fields
    motivation: Optional[str]          # Reason for travel (e.g., Honeymoon, Culture, Relaxation)
    transportation_pref: Optional[str] # FLIGHT | TRAIN | BUS | RENTAL
    activity_pref: Optional[str]       # NATURE | MUSEUM | NIGHTLIFE | SHOPPING
    dietary_pref: Optional[str]        # VEGAN | HALAL | GLUTEN_FREE | NONE

    destination_display: Optional[str] 
    origin_display: Optional[str]       
    budget_skipped: bool                
    
    # Tracking
    collected_fields: List[str]        # Which fields are filled
    
    # Plan
    plan_summary: Optional[str]        # Summary for user approval
    plan_approved: bool                # User approved the plan
    
    # Selections & Bookings
    selected_flight: Optional[dict]
    selected_hotel: Optional[dict]
    booking_ids: List[str]

class AgentState(TypedDict):
    """Main state for the workflow"""
    # Messages
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User info
    customer_id: str
    
    # FSM state
    current_state: ConversationState
    previous_state: Optional[ConversationState]
    
    # Travel context (Sharpener fills this)
    travel_context: Optional[TravelContext]
    
    # Intent (set by Supervisor initially)
    intent: Optional[str]
    intent_category: Optional[str]  # REACTIVE | PLANNING | INFO
    
    # Routing signals
    next_agent: Optional[str]
    plan_ready: bool                # Sharpener sets this when done
    needs_user_input: bool          # Waiting for user response
    
    # Safety counters
    sharpening_turns: int
    action_turns: int
    
    # Flags
    awaiting_confirmation: bool
    
    # Suggestions for the user (buttons, etc.)
    suggestions: Annotated[List[str], operator.add]  # ← FIX!
    
    # Completed tasks - CRITICAL FIX!
    completed_tasks: Annotated[List[str], operator.add]  # ← FIX!

# ═══════════════════════════════════════════════════════════════════
# REQUIRED FIELDS (UPDATED - Smart Grouping)
# ═══════════════════════════════════════════════════════════════════

# Zorunlu alanlar - bunlar OLMADAN arama yapılamaz
REQUIRED_FIELDS_CORE = ["destination", "departure_date", "return_date"]

# Önemli ama opsiyonel - varsa daha iyi sonuç
OPTIONAL_FIELDS_IMPORTANT = [
    "motivation",       # Neden? (öneriler için faydalı)
    "budget_max",       # Bütçe (filtreleme için)
]

# Tamamen opsiyonel - kullanıcı isterse
OPTIONAL_FIELDS_EXTRA = [
    "transportation_pref",  # Ulaşım tercihi
    "activity_pref",        # Aktivite tercihi  
    "dietary_pref",         # Diyet tercihi
]

# Eski değişken adını koru (uyumluluk için)
REQUIRED_FIELDS_TRIP = REQUIRED_FIELDS_CORE
REQUIRED_FIELDS_FLIGHT = ["destination", "departure_date", "travelers"]
REQUIRED_FIELDS_HOTEL = ["destination", "departure_date", "return_date", "travelers"]