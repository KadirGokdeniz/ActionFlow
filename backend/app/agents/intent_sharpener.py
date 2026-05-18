"""
ActionFlow - Intent Sharpener v3
Akıllı bilgi toplama, 4 turn limiti, varsayılanlar

Turn Yapısı:
1. Motivasyon + Destinasyon
2. Tarihler (gidiş + dönüş)
3. Bütçe (opsiyonel, geçilebilir)
4. Tercihler (ulaşım, aktivite, konaklama - sadece kullanıcı isterse)

Tek kişilik seyahat varsayımı.
"""

import logging
import json
from datetime import datetime
from langchain_core.messages import AIMessage, SystemMessage
from app.core.schemas import AgentState, ConversationState
from app.core.llm import llm

logger = logging.getLogger("ActionFlow-Sharpener")


# ═══════════════════════════════════════════════════════════════════
# FIELD DEFINITIONS
# ═══════════════════════════════════════════════════════════════════

REQUIRED_FIELDS = ["destination", "departure_date", "return_date"]

OPTIONAL_FIELDS = ["origin", "motivation", "budget_max", "budget_currency"]

PREFERENCE_FIELDS = ["transportation_pref", "activity_pref", "accommodation_pref"]

SMART_DEFAULTS = {
    "origin": None,  # Kullanıcıdan alınmalı veya None kalabilir
    "motivation": "general",
    "budget_max": None,  # Tüm seçenekleri göster
    "budget_currency": "EUR",
    "transportation_pref": "flexible",
    "activity_pref": "flexible",
    "accommodation_pref": "hotel",
    "travelers": 1,  # Sabit tek kişi
}

# Motivasyona göre destinasyon önerileri
DESTINATION_SUGGESTIONS = {
    "romantic": ["Paris", "Venedik", "Santorini", "Maldivler"],
    "adventure": ["İzlanda", "Yeni Zelanda", "Kosta Rika", "Nepal"],
    "relaxation": ["Bali", "Tayland", "Maldivler", "Hawaii"],
    "culture": ["Roma", "Tokyo", "İstanbul", "Barselona"],
    "budget": ["Portekiz", "Vietnam", "Yunanistan", "Türkiye"],
    "beach": ["Antalya", "Bali", "Maldivler", "Tayland"],
    "city": ["Londra", "New York", "Paris", "Tokyo"],
}


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def create_empty_travel_context() -> dict:
    """Boş travel context oluştur"""
    return {
        "destination": None,
        "destination_display": None,  # Kullanıcıya gösterilecek isim
        "origin": None,
        "origin_display": None,
        "departure_date": None,
        "return_date": None,
        "motivation": None,
        "budget_max": None,
        "budget_currency": "EUR",
        "transportation_pref": None,
        "activity_pref": None,
        "accommodation_pref": None,
        "travelers": 1,
        "collected_fields": [],
        "current_phase": 1,
    }


def get_current_phase(travel_context: dict) -> int:
    """Hangi fazda olduğumuzu belirle"""
    collected = travel_context.get("collected_fields", [])
    
    # Faz 1: Motivasyon + Destinasyon
    has_destination = "destination" in collected
    if not has_destination:
        return 1
    
    # Faz 2: Tarihler
    has_dates = "departure_date" in collected and "return_date" in collected
    if not has_dates:
        return 2
    
    # Faz 3: Bütçe
    has_budget = "budget_max" in collected or travel_context.get("budget_skipped")
    if not has_budget:
        return 3
    
    # Faz 4: Tamamlandı
    return 4


def check_completion(travel_context: dict) -> tuple[bool, list]:
    """Zorunlu alanların tamamlanıp tamamlanmadığını kontrol et"""
    collected = travel_context.get("collected_fields", [])
    missing = [f for f in REQUIRED_FIELDS if f not in collected]
    is_complete = len(missing) == 0
    return is_complete, missing


def apply_smart_defaults(travel_context: dict) -> dict:
    """Eksik opsiyonel alanları varsayılanlarla doldur"""
    for field, default_value in SMART_DEFAULTS.items():
        if travel_context.get(field) is None:
            travel_context[field] = default_value
    return travel_context


def format_collected_info(travel_context: dict, language: str = "tr") -> str:
    """Toplanan bilgileri formatla"""
    lines = []
    
    if travel_context.get("motivation"):
        label = "Motivasyon" if language == "tr" else "Motivation"
        lines.append(f"✓ {label}: {travel_context['motivation']}")
    
    dest = travel_context.get("destination_display") or travel_context.get("destination")
    if dest:
        label = "Destinasyon" if language == "tr" else "Destination"
        lines.append(f"✓ {label}: {dest}")
    
    origin = travel_context.get("origin_display") or travel_context.get("origin")
    if origin:
        label = "Kalkış" if language == "tr" else "Origin"
        lines.append(f"✓ {label}: {origin}")
    
    if travel_context.get("departure_date"):
        label = "Gidiş" if language == "tr" else "Departure"
        lines.append(f"✓ {label}: {travel_context['departure_date']}")
    
    if travel_context.get("return_date"):
        label = "Dönüş" if language == "tr" else "Return"
        lines.append(f"✓ {label}: {travel_context['return_date']}")
    
    if travel_context.get("budget_max"):
        label = "Bütçe" if language == "tr" else "Budget"
        currency = travel_context.get("budget_currency", "EUR")
        lines.append(f"✓ {label}: {travel_context['budget_max']} {currency}")
    
    return "\n".join(lines) if lines else "Henüz bilgi yok"


def create_plan_summary(travel_context: dict, language: str = "tr") -> str:
    """Seyahat planı özeti oluştur"""
    dest = travel_context.get("destination_display") or travel_context.get("destination")
    origin = travel_context.get("origin_display") or travel_context.get("origin")
    dep_date = travel_context.get("departure_date")
    ret_date = travel_context.get("return_date")
    budget = travel_context.get("budget_max")
    currency = travel_context.get("budget_currency", "EUR")
    motivation = travel_context.get("motivation")
    
    if language == "tr":
        lines = [f"📍 Destinasyon: {dest}"]
        if origin:
            lines.append(f"🛫 Kalkış: {origin}")
        lines.append(f"📅 Tarih: {dep_date} → {ret_date}")
        if budget:
            lines.append(f"💰 Bütçe: {budget} {currency}")
        if motivation and motivation != "general":
            lines.append(f"🎯 Amaç: {motivation}")
    else:
        lines = [f"📍 Destination: {dest}"]
        if origin:
            lines.append(f"🛫 Origin: {origin}")
        lines.append(f"📅 Dates: {dep_date} → {ret_date}")
        if budget:
            lines.append(f"💰 Budget: {budget} {currency}")
        if motivation and motivation != "general":
            lines.append(f"🎯 Purpose: {motivation}")
    
    return "\n".join(lines)


def get_phase_prompt(phase: int, language: str = "tr") -> dict:
    """Her faz için prompt bilgisi"""
    
    phases = {
        1: {
            "tr": {
                "task": "Motivasyon ve destinasyon bilgisini topla",
                "question_hint": "Nasıl bir tatil hayal ediyorsun? Aklında bir yer var mı?",
                "examples": [
                    "Romantik bir kaçamak için Paris",
                    "Macera dolu bir tatil için İzlanda", 
                    "Dinlenmek için Bali"
                ]
            },
            "en": {
                "task": "Collect motivation and destination",
                "question_hint": "What kind of trip are you dreaming of? Any destination in mind?",
                "examples": [
                    "Paris for a romantic getaway",
                    "Iceland for adventure",
                    "Bali for relaxation"
                ]
            }
        },
        2: {
            "tr": {
                "task": "Gidiş ve dönüş tarihlerini topla",
                "question_hint": "Ne zaman gitmek istiyorsun? Kaç gün kalmayı düşünüyorsun?",
                "examples": [
                    "15-20 Mayıs arası",
                    "Gelecek hafta, 5 gün",
                    "Yaz tatilinde, 1 hafta"
                ]
            },
            "en": {
                "task": "Collect departure and return dates",
                "question_hint": "When would you like to go? How long do you plan to stay?",
                "examples": [
                    "May 15-20",
                    "Next week, 5 days",
                    "Summer holiday, 1 week"
                ]
            }
        },
        3: {
            "tr": {
                "task": "Bütçe bilgisini topla (opsiyonel)",
                "question_hint": "Yaklaşık bir bütçen var mı? (İstemezsen geçebiliriz)",
                "examples": [
                    "1000-1500 Euro",
                    "Bütçe önemli değil",
                    "Geç, tüm seçenekleri göster"
                ]
            },
            "en": {
                "task": "Collect budget (optional)",
                "question_hint": "Do you have a budget in mind? (We can skip if you prefer)",
                "examples": [
                    "1000-1500 EUR",
                    "Budget doesn't matter",
                    "Skip, show all options"
                ]
            }
        },
        4: {
            "tr": {
                "task": "Plan özeti göster ve onay al",
                "question_hint": "İşte seyahat planın! Aramaya başlayalım mı?",
                "examples": []
            },
            "en": {
                "task": "Show plan summary and get confirmation",
                "question_hint": "Here's your travel plan! Ready to search?",
                "examples": []
            }
        }
    }
    
    return phases.get(phase, phases[1])[language]


# ═══════════════════════════════════════════════════════════════════
# MAIN SHARPENER NODE
# ═══════════════════════════════════════════════════════════════════

async def intent_sharpener_node(state: AgentState) -> dict:
    """
    Intent Sharpener v3 - 4 Turn Yapısı
    
    Turn 1: Motivasyon + Destinasyon
    Turn 2: Tarihler
    Turn 3: Bütçe (opsiyonel)
    Turn 4: Onay
    """
    logger.info("🎯 [SHARPENER] Processing travel information...")
    
    # State'ten bilgileri al
    travel_context = state.get("travel_context") or create_empty_travel_context()
    messages = state["messages"]
    turns = state.get("sharpening_turns", 0)
    language = state.get("language", "en")
    
    # Mevcut fazı belirle
    current_phase = get_current_phase(travel_context)
    phase_info = get_phase_prompt(current_phase, language)
    
    # Toplanan bilgileri formatla
    collected_info = format_collected_info(travel_context, language)
    
    # Tamamlanma kontrolü
    is_complete, missing_fields = check_completion(travel_context)
    
    # Bugünün tarihi (relative date hesaplaması için)
    today = datetime.now().strftime("%Y-%m-%d")
    
    # System prompt oluştur
    lang_instruction = "Respond ONLY in Turkish." if language == "tr" else "Respond ONLY in English."
    system_prompt = f"""You are a friendly travel assistant helping plan a trip.
Your goal: Collect travel information efficiently in maximum 4 turns.

╔══════════════════════════════════════════════════════════════════╗
║  🔴 CRITICAL: MANDATORY LANGUAGE REQUIREMENT                     ║
║  User's selected language: {language}                            ║
║  {lang_instruction}                                              ║
║  IGNORE the language of the user's message content.              ║
║  ALWAYS respond in {language} regardless of input language.      ║
║  This is NON-NEGOTIABLE.                                         ║
╚══════════════════════════════════════════════════════════════════╝


TODAY'S DATE: {today}

══════════════════════════════════════════
COLLECTED SO FAR:
{collected_info}

CURRENT PHASE: {current_phase}/4
TASK: {phase_info['task']}
QUESTION HINT: {phase_info['question_hint']}
══════════════════════════════════════════

PHASE GUIDE:
- Phase 1: Get MOTIVATION (why traveling) and DESTINATION (where)
- Phase 2: Get DATES (departure and return, convert relative dates to YYYY-MM-DD)
- Phase 3: Get BUDGET (optional - user can skip)
- Phase 4: Show summary and confirm

EXTRACTION RULES:
1. Extract ALL information from user's message (they might give multiple details at once)
2. For destinations: Extract the city/country NAME as-is (e.g., "Paris", "Londra", "İstanbul")
   - Do NOT convert to IATA codes, keep the original name
3. For dates: Convert relative dates to YYYY-MM-DD format
   - "next week" → calculate from {today}
   - "May 15" → 2026-05-15 (assume current/next year)
   - "5 days" → if departure known, calculate return date
4. For budget: Extract number and currency (default EUR if not specified)
5. If user says "skip", "geç", "no preference" for budget → mark as skipped

RESPONSE RULES:
- Keep responses SHORT (2-3 sentences max)
- Be warm and friendly
- Offer 2-3 quick suggestions when asking questions
- Use the user's language (Turkish or English based on their input)
- If Phase 4: Show the complete plan summary and ask for confirmation

RESPONSE FORMAT (JSON):
{{
    "extracted": {{
        "destination": "city/country name or null",
        "origin": "city/country name or null",
        "departure_date": "YYYY-MM-DD or null",
        "return_date": "YYYY-MM-DD or null",
        "motivation": "romantic/adventure/relaxation/culture/beach/city/budget/general or null",
        "budget_max": number or null,
        "budget_currency": "EUR/USD/TRY or null",
        "budget_skipped": true if user wants to skip budget else null
    }},
    "phase_complete": true if current phase goals achieved,
    "all_required_complete": true if destination + dates are all filled,
    "detected_language": "tr" or "en",
    "response": "Your friendly response in the detected language"
}}
"""

    # LLM çağrısı
    response = await llm.ainvoke(
        [SystemMessage(content=system_prompt)] + messages,
        response_format={"type": "json_object"}
    )
    
    # JSON parse
    try:
        result = json.loads(response.content)
    except json.JSONDecodeError:
        logger.warning(f"[SHARPENER] Non-JSON response: {response.content[:200]}")
        result = {
            "extracted": {},
            "all_required_complete": False,
            "response": response.content
        }
    
    # Extracted bilgileri context'e ekle
    extracted = result.get("extracted", {})
    for field, value in extracted.items():
        if value is not None:
            travel_context[field] = value
            if field not in travel_context.get("collected_fields", []):
                travel_context["collected_fields"] = travel_context.get("collected_fields", []) + [field]
    
    # Dil tespiti
    detected_language = language
    
    # Budget skip kontrolü
    if extracted.get("budget_skipped"):
        travel_context["budget_skipped"] = True
    
    # Tamamlanma kontrolü (tekrar)
    is_complete, missing_fields = check_completion(travel_context)
    llm_says_complete = result.get("all_required_complete", False)
    
    # Turn limiti kontrolü - 4 turn'dan sonra varsayılanları uygula
    if turns >= 3 and not is_complete:
        logger.info("⚠️ [SHARPENER] Turn limit reached, applying defaults")
        travel_context = apply_smart_defaults(travel_context)
        is_complete, missing_fields = check_completion(travel_context)
    
    # Tamamlandıysa plan özetini oluştur
    if is_complete or llm_says_complete:
        # Varsayılanları uygula
        travel_context = apply_smart_defaults(travel_context)
        
        # Plan özeti
        plan_summary = create_plan_summary(travel_context, detected_language)
        travel_context["plan_summary"] = plan_summary
        
        logger.info("✅ [SHARPENER] All info collected, plan ready!")
        
        # Yanıt metni
        response_text = result.get("response", "")
        
        # Plan özetini ekle (eğer yoksa)
        if plan_summary and "plan" not in response_text.lower():
            if detected_language == "tr":
                response_text = f"{response_text}\n\n📋 **Seyahat Planın:**\n{plan_summary}\n\n✅ Aramaya başlayalım mı?"
            else:
                response_text = f"{response_text}\n\n📋 **Your Travel Plan:**\n{plan_summary}\n\n✅ Ready to search?"
        
        return {
            "messages": [AIMessage(content=response_text)],
            "travel_context": travel_context,
            "plan_ready": True,
            "needs_user_input": False,
            "language": detected_language,
            "current_state": ConversationState.READY_FOR_ACTION
        }
    
    else:
        # Devam et
        new_phase = get_current_phase(travel_context)
        logger.info(f"📝 [SHARPENER] Phase {new_phase}/4, Missing: {missing_fields}, Turn: {turns + 1}")
        
        return {
            "messages": [AIMessage(content=result.get("response", "Tell me more about your trip!"))],
            "travel_context": travel_context,
            "plan_ready": False,
            "needs_user_input": True,
            "language": detected_language,
            "sharpening_turns": turns + 1,
            "current_state": ConversationState.SHARPENING
        }