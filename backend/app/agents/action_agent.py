"""
ActionFlow - Action Agent v4
Faz bazlı aksiyon yönetimi + Booking entegrasyonu

Fazlar:
1. SEARCH   - Uçuş/otel araması yap
2. PRESENT  - Sonuçları kullanıcıya göster
3. CONFIRM  - Kullanıcı seçimini onayla
4. BOOK     - Rezervasyonu gerçekleştir (create_booking tool)
5. COMPLETE - İşlem tamamlandı

Her faz için ayrı prompt ve mantık.
"""

import logging
import re
import json
from typing import Optional, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from app.core.schemas import AgentState
from app.core.utils import get_system_context
from app.core.llm import llm
from app.core.tools import action_tools
from app.core.metrics import track_agent
from app.core.tools.location import location_tools

logger = logging.getLogger("ActionFlow-ActionAgent")


# ═══════════════════════════════════════════════════════════════════
# PHASE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════

class ActionPhase:
    SEARCH = "search"       # Arama yapılacak
    PRESENT = "present"     # Sonuçlar gösterilecek
    CONFIRM = "confirm"     # Onay bekliyor
    BOOK = "book"           # Rezervasyon yapılacak
    COMPLETE = "complete"   # Tamamlandı


# Tool koleksiyonları
all_action_tools = action_tools + location_tools


# ═══════════════════════════════════════════════════════════════════
# PHASE DETECTION
# ═══════════════════════════════════════════════════════════════════

def determine_phase(state: AgentState) -> str:
    """
    Mevcut state'e bakarak hangi fazda olduğumuzu belirle
    """
    messages = state.get("messages", [])
    completed_tasks = state.get("completed_tasks", [])
    
    if not messages:
        return ActionPhase.SEARCH
    
    # Booking tamamlandı mı?
    if "booking_completed" in completed_tasks:
        return ActionPhase.COMPLETE
    
    # Kullanıcı onay verdi mi? (seçim + "evet/book it")
    if user_confirmation := _detect_user_confirmation(messages):
        if "selection_presented" in completed_tasks:
            return ActionPhase.BOOK
    
    # Kullanıcı seçim yaptı mı? (1, 2, "first option" vb.)
    if user_selection := _detect_user_selection(messages):
        if "results_presented" in completed_tasks:
            return ActionPhase.CONFIRM
    
    # CRITICAL FIX: Check if search was initiated
    if "search_initiated" in completed_tasks and "results_presented" not in completed_tasks:
        logger.info("🔍 [PHASE] Search initiated, routing to PRESENT")
        return ActionPhase.PRESENT
    
    # Sonuçlar gösterildi mi?
    if "results_presented" in completed_tasks and not user_selection:
        # Kullanıcı cevap bekleniyor, aynı fazda kal
        return ActionPhase.PRESENT
    
    # Varsayılan: Arama yap
    return ActionPhase.SEARCH


def _check_tool_results(messages: list) -> bool:
    """Son mesajlarda tool sonucu var mı?"""
    for msg in reversed(messages[-5:]):
        if msg.__class__.__name__ == 'ToolMessage':
            return True
        if hasattr(msg, 'type') and msg.type == 'tool':
            return True
    return False


def _check_ai_content(message: BaseMessage) -> bool:
    """AI mesajında içerik var mı (tool call değil)?"""
    if not message:
        return False
    if hasattr(message, 'content') and message.content:
        if not (hasattr(message, 'tool_calls') and message.tool_calls):
            return True
    return False


def _detect_user_selection(messages: list) -> Optional[dict]:
    """Kullanıcı bir seçim yaptı mı?"""
    # Son kullanıcı mesajını bul
    for msg in reversed(messages[-3:]):
        if isinstance(msg, HumanMessage):
            content = msg.content.lower()
            
            # Numara seçimi: "1", "2", "option 1", "1. seçenek"
            number_match = re.search(r'\b([1-5])\b', content)
            if number_match:
                return {"type": "number", "value": int(number_match.group(1))}
            
            # Kelime seçimi: "first", "second", "ilk", "birinci"
            ordinal_map = {
                "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
                "ilk": 1, "birinci": 1, "ikinci": 2, "ucuncu": 3, "dorduncu": 4,
                "1.": 1, "2.": 2, "3.": 3
            }
            # Türkçe karakterleri normalize et
            content_normalized = content.replace("ü", "u").replace("ö", "o").replace("ç", "c").replace("ı", "i")
            for word, num in ordinal_map.items():
                if word in content or word in content_normalized:
                    return {"type": "ordinal", "value": num}
            
            # "the cheapest", "en ucuz" gibi
            if any(kw in content for kw in ["cheapest", "en ucuz", "ucuz olan", "first one", "ilk"]):
                return {"type": "preference", "value": 1}
            
            break
    
    return None


def _detect_user_confirmation(messages: list) -> bool:
    """Kullanıcı onay verdi mi?"""
    for msg in reversed(messages[-2:]):
        if isinstance(msg, HumanMessage):
            content = msg.content.lower()
            
            confirm_keywords = [
                # English
                "yes", "yeah", "yep", "sure", "ok", "okay", "confirm", "book it",
                "go ahead", "proceed", "do it", "please book", "make the booking",
                "let's do it", "sounds good", "perfect", "great",
                # Turkish
                "evet", "tamam", "olur", "onayla", "rezerve et", "ayır",
                "yap", "devam", "kesinlikle", "tabi", "rezervasyon yap"
            ]
            
            if any(kw in content for kw in confirm_keywords):
                return True
            
            break
    
    return False


def _extract_passenger_info(state: AgentState) -> Dict[str, Any]:
    """
    State'den veya conversation'dan yolcu bilgilerini çıkar.
    Demo için varsayılan değerler kullanılır.
    """
    travel_context = state.get("travel_context") or {}
    customer_id = state.get("customer_id", "anonymous")
    
    # Gerçek implementasyonda bu bilgiler kullanıcıdan alınır
    # Demo için varsayılan değerler
    return {
        "first_name": "Demo",
        "last_name": "User",
        "email": f"{customer_id}@actionflow.demo",
        "phone": None
    }


def _extract_selected_offers(state: AgentState) -> Dict[str, Any]:
    """
    Conversation history'den seçilen offer ID'lerini çıkar.
    Demo için fake offer ID'leri döndürür.
    """
    travel_context = state.get("travel_context") or {}
    
    # Gerçek implementasyonda tool sonuçlarından parse edilir
    # Demo için fake ID'ler
    return {
        "flight_offer_id": f"FL-{travel_context.get('destination', 'PAR')}-001",
        "hotel_offer_id": f"HT-{travel_context.get('destination', 'PAR')}-001"
    }


# ═══════════════════════════════════════════════════════════════════
# MAIN NODE
# ═══════════════════════════════════════════════════════════════════

@track_agent("action")
async def action_agent_node(state: AgentState) -> dict:
    """
    Action Agent v4 - Phase-based execution with booking integration
    """
    # Fazı belirle
    phase = determine_phase(state)
    logger.info(f"🚀 [ACTION_AGENT] Phase: {phase}")
    
    # Faza göre işlem yap
    if phase == ActionPhase.SEARCH:
        return await _handle_search_phase(state)
    
    elif phase == ActionPhase.PRESENT:
        return await _handle_present_phase(state)
    
    elif phase == ActionPhase.CONFIRM:
        return await _handle_confirm_phase(state)
    
    elif phase == ActionPhase.BOOK:
        return await _handle_book_phase(state)
    
    elif phase == ActionPhase.COMPLETE:
        return await _handle_complete_phase(state)
    
    else:
        # Fallback
        return await _handle_search_phase(state)


# ═══════════════════════════════════════════════════════════════════
# PHASE HANDLERS
# ═══════════════════════════════════════════════════════════════════

async def _handle_search_phase(state: AgentState) -> dict:
    """SEARCH: Uçuş/otel araması yap"""
    logger.info("🔍 [ACTION_AGENT] Search phase")
    
    messages = state.get("messages", [])
    
    # ═══════════════════════════════════════════════════════════════
    # CRITICAL FIX: Prevent re-searching if we already have results!
    # ═══════════════════════════════════════════════════════════════
    for msg in reversed(messages[-5:]):
        msg_type = str(type(msg).__name__)
        if "ToolMessage" in msg_type or "Tool" in msg_type:
            logger.info("✅ [SEARCH] Tool results detected, marking search complete")
            return {
                "messages": [AIMessage(content="Search completed. Results ready to present.")],
                "completed_tasks": state.get("completed_tasks", []) + ["search_initiated"]
            }
    
    context = get_system_context()
    customer_id = state.get("customer_id", "anonymous")
    travel_context = state.get("travel_context") or {}
    language = state.get("language", "en")
    
    plan_info = _format_travel_plan(travel_context)
    lang_instruction = "Respond in Turkish." if language == "tr" else "Respond in English."
    
    system_prompt = f"""You are a travel booking assistant. {context}

════════════════════════════════════════════════════════════════════
CRITICAL: Language Preference
{lang_instruction}
════════════════════════════════════════════════════════════════════

CUSTOMER ID: {customer_id}

{f"TRAVEL PLAN:{chr(10)}{plan_info}" if plan_info else "No specific plan yet."}

═══════════════════════════════════════════════════════════════
PHASE: SEARCH
YOUR TASK: Execute flight and/or hotel searches
═══════════════════════════════════════════════════════════════

AVAILABLE TOOLS:

**Location (use first if needed):**
- resolve_location: Convert city name → IATA code
- validate_route: Validate origin + destination together

**Search:**
- search_flights: Search flights (needs IATA codes)
- search_hotels: Search hotels (needs IATA city code)
- get_hotel_offers: Get hotel prices for specific hotels

**Bookings:**
- get_user_bookings: List user's bookings (user_id="{customer_id}")
- cancel_booking: Cancel a booking (confirm with user first!)
- modify_booking: Modify dates (confirm with user first!)

WORKFLOW:
1. If you have city names → call resolve_location first
2. Then call search_flights and/or search_hotels
3. Do NOT present results yet, just execute the searches

RULES:
- Never guess IATA codes
- Execute searches based on the travel plan
- For cancellations: always confirm first

{lang_instruction}
"""
    
    llm_with_tools = llm.bind_tools(all_action_tools)
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    
    # Mark that we've initiated a search
    new_tasks = state.get("completed_tasks", []).copy()
    if hasattr(response, 'tool_calls') and response.tool_calls:
        if "search_initiated" not in new_tasks:
            new_tasks.append("search_initiated")
            logger.info("✅ [ACTION_AGENT] Search initiated, tools called")
    
    return {
        "messages": [response],
        "completed_tasks": new_tasks
    }


async def _handle_present_phase(state: AgentState) -> dict:
    """PRESENT: Sonuçları göster"""
    logger.info("📋 [ACTION_AGENT] Present phase")
    
    context = get_system_context()
    language = state.get("language", "en")
    lang_instruction = "Respond in Turkish." if language == "tr" else "Respond in English."
    
    messages = state.get("messages", [])
    
    # Find last user message
    last_user_msg = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg
            break
    
    # Extract tool results as TEXT (not ToolMessage objects!)
    tool_results_text = ""
    for msg in reversed(messages[-10:]):
        msg_type = str(type(msg).__name__)
        if "Tool" in msg_type and hasattr(msg, 'content'):
            tool_results_text += f"\n{msg.content}\n"
    
    # Build user message with embedded results
    if last_user_msg and tool_results_text:
        combined_content = f"{last_user_msg.content}\n\n[SEARCH RESULTS]:\n{tool_results_text}"
        user_msg_with_results = HumanMessage(content=combined_content)
    elif last_user_msg:
        user_msg_with_results = last_user_msg
    else:
        user_msg_with_results = HumanMessage(content="Present the search results.")
    
    system_prompt = f"""You are a travel booking assistant. {context}

════════════════════════════════════════════════════════════════════
CRITICAL: Language Preference
{lang_instruction}
════════════════════════════════════════════════════════════════════
    
═══════════════════════════════════════════════════════════════
PHASE: PRESENT RESULTS
YOUR TASK: Show search results clearly to the user
═══════════════════════════════════════════════════════════════

The user's message contains search results. Present them in this format:

✈️ **Flight Options:**

1. **[Airline]** - [Price] EUR
   🛫 [Departure] → 🛬 [Arrival]
   ⏱️ [Duration] | Stops: [N]

2. **[Airline]** - [Price] EUR
   🛫 [Departure] → 🛬 [Arrival]
   ⏱️ [Duration] | Stops: [N]

(Show up to 3 best options)

💡 **Which option would you like? Just tell me the number!**

RULES:
- Number all options clearly (1, 2, 3...)
- Show prices with currency
- Keep it brief and scannable
- Show max 3 options
- Ask user to pick a number

{lang_instruction}
"""
    
    # Use simple message structure
    minimal_messages = [
        SystemMessage(content=system_prompt),
        user_msg_with_results
    ]
    
    logger.info(f"📋 [PRESENT] Using 2 messages (system + user with embedded results)")
    
    response = await llm.ainvoke(minimal_messages)
    
    # Task güncelle
    new_tasks = state.get("completed_tasks", []).copy()
    if "results_presented" not in new_tasks:
        new_tasks.append("results_presented")
    
    return {
        "messages": [response],
        "completed_tasks": new_tasks
    }



async def _handle_confirm_phase(state: AgentState) -> dict:
    """CONFIRM: Kullanıcı seçimini onayla"""
    logger.info("✅ [ACTION_AGENT] Confirm phase")
    
    context = get_system_context()
    language = state.get("language", "en")
    travel_context = state.get("travel_context") or {}
    
    # Seçimi tespit et
    selection = _detect_user_selection(state["messages"])
    selection_text = f"Selection: Option {selection['value']}" if selection else "Selection not clear"
    
    lang_instruction = "Respond in Turkish." if language == "tr" else "Respond in English."
    
    if language == "tr":
        confirm_template = """Harika seçim! İşte seçtiğin detaylar:

**✈️ Uçuş:** [Havayolu] [Uçuş No]
- Tarih: [Tarih]
- Kalkış: [Saat] → Varış: [Saat]
- Fiyat: [Fiyat] EUR

**🏨 Otel:** [Otel Adı]
- Giriş: [Giriş Tarihi]
- Çıkış: [Çıkış Tarihi]
- Fiyat: [Fiyat] EUR/gece

**💰 Toplam:** [Toplam] EUR

Rezervasyonu onaylıyor musun?"""
    else:
        confirm_template = """Great choice! Here's your selection:

**✈️ Flight:** [Airline] [Flight No]
- Date: [Date]
- Departure: [Time] → Arrival: [Time]
- Price: [Price] EUR

**🏨 Hotel:** [Hotel Name]
- Check-in: [Check-in Date]
- Check-out: [Check-out Date]
- Price: [Price] EUR/night

**💰 Total:** [Total] EUR

Would you like to confirm this booking?"""
    
    system_prompt = f"""You are a travel booking assistant. {context}

════════════════════════════════════════════════════════════════════
CRITICAL: Language Preference
{lang_instruction}
════════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════
PHASE: CONFIRM SELECTION
YOUR TASK: Confirm user's selection and ask for booking approval
═══════════════════════════════════════════════════════════════

{selection_text}

Show the selected option details and ask for confirmation:

{confirm_template}

RULES:
- Be clear about what they selected
- Show all details (price, time, location)
- Ask explicitly: "Would you like to proceed?"
- If selection is unclear, ask them to clarify

{lang_instruction}
"""
    
    # NO TOOLS in CONFIRM - just confirm selection!
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm.ainvoke(messages)
    
    # Task güncelle
    new_tasks = state.get("completed_tasks", []).copy()
    if "selection_presented" not in new_tasks:
        new_tasks.append("selection_presented")
    
    return {
        "messages": [response],
        "completed_tasks": new_tasks,
        "awaiting_confirmation": True
    }


async def _handle_book_phase(state: AgentState) -> dict:
    """BOOK: Rezervasyonu gerçekleştir"""
    logger.info("📝 [ACTION_AGENT] Book phase")
    
    from app.core.tools.booking import booking_tools
    
    context = get_system_context()
    language = state.get("language", "en")
    travel_context = state.get("travel_context") or {}
    customer_id = state.get("customer_id", "anonymous")
    
    # Yolcu bilgileri ve seçilen offer'lar
    passenger_info = _extract_passenger_info(state)
    selected_offers = _extract_selected_offers(state)
    
    lang_instruction = "Respond in Turkish." if language == "tr" else "Respond in English."
    
    system_prompt = f"""You are a travel booking assistant. {context}

════════════════════════════════════════════════════════════════════
CRITICAL: Language Preference
{lang_instruction}
════════════════════════════════════════════════════════════════════

CUSTOMER ID: {customer_id}

═══════════════════════════════════════════════════════════════
PHASE: CREATE BOOKING
YOUR TASK: Execute the booking with create_booking tool
═══════════════════════════════════════════════════════════════

PASSENGER INFO:
{json.dumps(passenger_info, indent=2)}

SELECTED OFFERS:
{json.dumps(selected_offers, indent=2)}

WORKFLOW:
1. Call create_booking tool with:
   - customer_id: "{customer_id}"
   - passenger_info: {passenger_info}
   - selected_offers: {selected_offers}

2. After successful booking, show confirmation:

✅ **Booking Confirmed!**

📧 Confirmation sent to: [Email]
🎫 Booking Reference: [Ref]

**Flight Details:**
✈️ [Flight Info]

**Hotel Details:**
🏨 [Hotel Info]

💰 **Total:** [Amount] EUR

Thank the user and ask if they need anything else.

{lang_instruction}
"""
    
    # Only booking tool needed in BOOK phase
    llm_with_booking = llm.bind_tools(booking_tools)
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm_with_booking.ainvoke(messages)
    
    # Task güncelle
    new_tasks = state.get("completed_tasks", []).copy()
    if "booking_completed" not in new_tasks:
        new_tasks.append("booking_completed")
    if "action_completed" not in new_tasks:
        new_tasks.append("action_completed")
    
    return {
        "messages": [response],
        "completed_tasks": new_tasks,
        "awaiting_confirmation": False
    }


async def _handle_complete_phase(state: AgentState) -> dict:
    """COMPLETE: İşlem tamamlandı"""
    logger.info("🏁 [ACTION_AGENT] Complete phase")
    
    language = state.get("language", "en")
    
    if language == "tr":
        message = "Rezervasyonunuz tamamlandı! 🎉 Başka bir konuda yardımcı olabilir miyim?"
    else:
        message = "Your booking is complete! 🎉 Is there anything else I can help you with?"
    
    return {
        "messages": [AIMessage(content=message)],
        "completed_tasks": state.get("completed_tasks", []).copy()
    }


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def _format_travel_plan(travel_context: dict) -> str:
    """Travel context'i okunabilir formata çevir"""
    if not travel_context:
        return ""
    
    lines = []
    
    dest = travel_context.get("destination_display") or travel_context.get("destination")
    if dest:
        lines.append(f"📍 Destination: {dest}")
    
    origin = travel_context.get("origin_display") or travel_context.get("origin")
    if origin:
        lines.append(f"🛫 Origin: {origin}")
    
    if travel_context.get("departure_date"):
        lines.append(f"📅 Departure: {travel_context['departure_date']}")
    
    if travel_context.get("return_date"):
        lines.append(f"📅 Return: {travel_context['return_date']}")
    
    if travel_context.get("travelers"):
        lines.append(f"👥 Travelers: {travel_context['travelers']}")
    
    if travel_context.get("budget_max"):
        currency = travel_context.get("budget_currency", "EUR")
        lines.append(f"💰 Budget: {travel_context['budget_max']} {currency}")
    
    if travel_context.get("motivation"):
        lines.append(f"🎯 Purpose: {travel_context['motivation']}")
    
    return "\n".join(lines)