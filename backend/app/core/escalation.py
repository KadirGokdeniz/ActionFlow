"""
ActionFlow - Escalation Analyzer
LLM tabanlı sentiment analizi ve escalation karar mekanizması

Eski yaklaşım: Keyword bazlı ("human", "manager", "yetkili")
Yeni yaklaşım: Çoklu sinyal analizi + LLM sentiment

Sinyaller:
1. Explicit request - Kullanıcı açıkça insan istiyor
2. Frustration level - Sinirli/kızgın ton
3. Repeated failures - Aynı istek 3+ kez
4. Issue complexity - Çoklu problem, edge case
5. Payment dispute - Ödeme/iade anlaşmazlığı
"""

import logging
import json
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from app.core.llm import llm

logger = logging.getLogger("ActionFlow-Escalation")


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Escalation eşik skoru (0-100)
ESCALATION_THRESHOLD = 50

# Sinyal ağırlıkları
SIGNAL_WEIGHTS = {
    "explicit_request": 50,      # Direkt insan isterse
    "high_frustration": 30,      # Çok sinirli (level 4-5)
    "medium_frustration": 15,    # Orta sinirli (level 3)
    "repeated_requests": 25,     # 3+ aynı istek
    "complex_issue": 20,         # Karmaşık problem
    "payment_dispute": 15,       # Ödeme sorunu
    "conversation_length": 10,   # Çok uzun konuşma (10+ turn)
}


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_recent_messages(messages: List[BaseMessage], count: int = 6) -> List[BaseMessage]:
    """Son N mesajı al"""
    return messages[-count:] if len(messages) > count else messages


def format_messages_for_analysis(messages: List[BaseMessage]) -> str:
    """Mesajları analiz için formatla"""
    formatted = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            formatted.append(f"USER: {msg.content}")
        elif isinstance(msg, AIMessage):
            # Tool call'ları atla, sadece içerik
            if msg.content:
                formatted.append(f"ASSISTANT: {msg.content[:200]}...")
    return "\n".join(formatted)


def count_user_messages(messages: List[BaseMessage]) -> int:
    """Kullanıcı mesaj sayısını say"""
    return sum(1 for msg in messages if isinstance(msg, HumanMessage))


def detect_repeated_requests(messages: List[BaseMessage]) -> int:
    """Benzer isteklerin tekrar sayısını tespit et"""
    user_messages = [msg.content.lower() for msg in messages if isinstance(msg, HumanMessage)]
    
    if len(user_messages) < 2:
        return 0
    
    last_msg = user_messages[-1]
    similar_count = 0
    
    # Anahtar kelimeleri çıkar (stop words hariç)
    stop_words = {"i", "the", "a", "an", "to", "my", "please", "said", "want", "need", "can", "you"}
    last_words = set(last_msg.split()) - stop_words
    
    for prev_msg in user_messages[:-1]:
        prev_words = set(prev_msg.split()) - stop_words
        
        # Ortak kelime oranı
        if last_words and prev_words:
            common = len(last_words & prev_words)
            ratio = common / min(len(last_words), len(prev_words))
            if ratio > 0.4:  # %40 benzerlik yeterli
                similar_count += 1
    
    return similar_count


# ═══════════════════════════════════════════════════════════════════
# MAIN ANALYZER
# ═══════════════════════════════════════════════════════════════════

async def analyze_escalation_need(
    messages: List[BaseMessage],
    travel_context: Optional[dict] = None,
    failed_actions: Optional[List[str]] = None
) -> dict:
    """
    Escalation ihtiyacını analiz et
    
    Args:
        messages: Konuşma geçmişi
        travel_context: Seyahat bağlamı
        failed_actions: Başarısız olan işlemler listesi
    
    Returns:
        {
            "should_escalate": bool,
            "score": int (0-100),
            "signals": {...},
            "reason": str,
            "urgency": "low" | "medium" | "high"
        }
    """
    logger.info("🔍 [ESCALATION] Analyzing escalation need...")
    
    # Temel kontroller
    if not messages:
        return _no_escalation("No messages to analyze")
    
    user_message_count = count_user_messages(messages)
    recent_messages = get_recent_messages(messages, 6)
    
    # ─────────────────────────────────────────────────────────────
    # LLM ile sentiment analizi
    # ─────────────────────────────────────────────────────────────
    
    conversation_text = format_messages_for_analysis(recent_messages)
    
    analysis_prompt = f"""Analyze this customer service conversation for escalation signals.

CONVERSATION:
{conversation_text}

Analyze and return JSON:
{{
    "explicit_human_request": true if user explicitly asks for human/manager/representative,
    "frustration_level": 1-5 (1=calm, 5=very angry),
    "frustration_indicators": ["list", "of", "indicators"],
    "issue_type": "booking" | "cancellation" | "refund" | "complaint" | "info" | "other",
    "involves_payment": true if money/refund/payment is discussed,
    "issue_complexity": 1-5 (1=simple, 5=very complex),
    "user_sentiment": "positive" | "neutral" | "negative" | "very_negative",
    "key_concerns": ["main", "user", "concerns"],
    "recommended_action": "continue" | "escalate" | "urgent_escalate"
}}

Be objective. Consider:
- Tone and word choice
- Repeated complaints
- Unresolved issues
- Payment/refund disputes
- Explicit requests for human help
"""
    
    try:
        response = await llm.ainvoke(
            [SystemMessage(content=analysis_prompt)],
            response_format={"type": "json_object"}
        )
        analysis = json.loads(response.content)
    except Exception as e:
        logger.warning(f"[ESCALATION] LLM analysis failed: {e}")
        # Fallback: Basit kontrol
        analysis = _fallback_analysis(messages)
    
    # ─────────────────────────────────────────────────────────────
    # Skor hesaplama
    # ─────────────────────────────────────────────────────────────
    
    score = 0
    signals = {}
    
    # 1. Explicit request
    if analysis.get("explicit_human_request"):
        score += SIGNAL_WEIGHTS["explicit_request"]
        signals["explicit_request"] = True
    
    # 2. Frustration level
    frustration = analysis.get("frustration_level", 1)
    if frustration >= 4:
        score += SIGNAL_WEIGHTS["high_frustration"]
        signals["high_frustration"] = True
    elif frustration == 3:
        score += SIGNAL_WEIGHTS["medium_frustration"]
        signals["medium_frustration"] = True
    
    # 3. Repeated requests
    repeated = detect_repeated_requests(messages)
    if repeated >= 3:
        score += SIGNAL_WEIGHTS["repeated_requests"]
        signals["repeated_requests"] = repeated
    
    # 4. Issue complexity
    complexity = analysis.get("issue_complexity", 1)
    if complexity >= 4:
        score += SIGNAL_WEIGHTS["complex_issue"]
        signals["complex_issue"] = True
    
    # 5. Payment dispute
    if analysis.get("involves_payment") and analysis.get("user_sentiment") in ["negative", "very_negative"]:
        score += SIGNAL_WEIGHTS["payment_dispute"]
        signals["payment_dispute"] = True
    
    # 6. Conversation length
    if user_message_count >= 10:
        score += SIGNAL_WEIGHTS["conversation_length"]
        signals["long_conversation"] = user_message_count
    
    # 7. Failed actions bonus
    if failed_actions and len(failed_actions) >= 2:
        score += 15
        signals["failed_actions"] = failed_actions
    
    # ─────────────────────────────────────────────────────────────
    # Karar
    # ─────────────────────────────────────────────────────────────
    
    should_escalate = score >= ESCALATION_THRESHOLD
    
    # Urgency belirleme
    if score >= 70:
        urgency = "high"
    elif score >= 50:
        urgency = "medium"
    else:
        urgency = "low"
    
    # Reason oluşturma
    reason = _build_escalation_reason(signals, analysis, should_escalate)
    
    result = {
        "should_escalate": should_escalate,
        "score": score,
        "threshold": ESCALATION_THRESHOLD,
        "signals": signals,
        "analysis": {
            "frustration_level": analysis.get("frustration_level"),
            "sentiment": analysis.get("user_sentiment"),
            "issue_type": analysis.get("issue_type"),
            "key_concerns": analysis.get("key_concerns", []),
        },
        "reason": reason,
        "urgency": urgency,
        "recommended_action": analysis.get("recommended_action", "continue")
    }
    
    logger.info(f"📊 [ESCALATION] Score: {score}/{ESCALATION_THRESHOLD}, Escalate: {should_escalate}, Urgency: {urgency}")
    
    return result


def _no_escalation(reason: str) -> dict:
    """Escalation yok döndür"""
    return {
        "should_escalate": False,
        "score": 0,
        "threshold": ESCALATION_THRESHOLD,
        "signals": {},
        "analysis": {},
        "reason": reason,
        "urgency": "low",
        "recommended_action": "continue"
    }


def _fallback_analysis(messages: List[BaseMessage]) -> dict:
    """LLM başarısız olursa basit analiz"""
    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content.lower()
            break
    
    # Basit keyword kontrolü (fallback)
    explicit_keywords = ["human", "agent", "representative", "manager", "insan", "yetkili", "müdür", "şikayet"]
    frustration_keywords = ["terrible", "awful", "worst", "angry", "furious", "unacceptable", 
                           "berbat", "rezalet", "kabul edilemez", "sinir", "kızgın"]
    payment_keywords = ["refund", "money", "payment", "charge", "iade", "para", "ödeme", "ücret"]
    
    return {
        "explicit_human_request": any(kw in last_user_msg for kw in explicit_keywords),
        "frustration_level": 4 if any(kw in last_user_msg for kw in frustration_keywords) else 2,
        "involves_payment": any(kw in last_user_msg for kw in payment_keywords),
        "issue_complexity": 2,
        "user_sentiment": "negative" if any(kw in last_user_msg for kw in frustration_keywords) else "neutral",
        "key_concerns": [],
        "recommended_action": "continue"
    }


def _build_escalation_reason(signals: dict, analysis: dict, should_escalate: bool) -> str:
    """Escalation sebebini oluştur"""
    if not should_escalate:
        return "No escalation needed - conversation proceeding normally"
    
    reasons = []
    
    if signals.get("explicit_request"):
        reasons.append("User explicitly requested human assistance")
    
    if signals.get("high_frustration"):
        reasons.append(f"High frustration level detected (level {analysis.get('frustration_level', '?')})")
    
    if signals.get("repeated_requests"):
        reasons.append(f"Same request repeated {signals['repeated_requests']} times")
    
    if signals.get("payment_dispute"):
        reasons.append("Payment/refund dispute with negative sentiment")
    
    if signals.get("complex_issue"):
        reasons.append("Complex issue requiring human judgment")
    
    if signals.get("long_conversation"):
        reasons.append(f"Extended conversation ({signals['long_conversation']} messages) without resolution")
    
    if signals.get("failed_actions"):
        reasons.append(f"Multiple failed actions: {', '.join(signals['failed_actions'])}")
    
    return "; ".join(reasons) if reasons else "Multiple escalation signals detected"


# ═══════════════════════════════════════════════════════════════════
# QUICK CHECK (for supervisor)
# ═══════════════════════════════════════════════════════════════════

async def quick_escalation_check(last_message: str) -> bool:
    """
    Hızlı escalation kontrolü (supervisor için)
    Sadece açık insan talebi varsa True döner
    
    Full analiz için analyze_escalation_need kullan
    """
    if not last_message:
        return False
    
    msg_lower = last_message.lower()
    
    # Açık insan talebi keywords
    explicit_keywords = [
        # English
        "speak to human", "talk to human", "human agent", "real person",
        "speak to someone", "talk to someone", "representative", "manager",
        "supervisor", "escalate", "complaint department",
        # Turkish
        "insanla görüşmek", "gerçek biri", "yetkili", "müdür", 
        "şikayet", "üst makam", "temsilci"
    ]
    
    return any(kw in msg_lower for kw in explicit_keywords)


# ═══════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════

__all__ = [
    "analyze_escalation_need",
    "quick_escalation_check",
    "ESCALATION_THRESHOLD",
    "SIGNAL_WEIGHTS"
]