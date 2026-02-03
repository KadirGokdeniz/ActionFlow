"""
ActionFlow - Supervisor v2
Ana routing mantığı + sentiment-based escalation

Değişiklikler (v2):
- Keyword bazlı escalation kaldırıldı
- LLM sentiment analizi eklendi
- quick_escalation_check ile hızlı kontrol
- Detaylı analiz için analyze_escalation_need
"""

import logging
import json
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.schemas import AgentState, ConversationState
from app.core.utils import create_empty_travel_context
from app.core.llm import llm
from app.core.escalation import quick_escalation_check, analyze_escalation_need

logger = logging.getLogger("ActionFlow-Supervisor")


async def supervisor_node(state: AgentState) -> dict:
    """
    Supervisor v2 - Intelligent routing with sentiment-based escalation
    """
    logger.info(f"🔍 [SUPERVISOR] State: {state.get('current_state', 'IDLE')}, plan_ready: {state.get('plan_ready', False)}")
    
    current_state = state.get("current_state", ConversationState.IDLE)
    messages = state["messages"]
    language = state.get("language", "en")
    
    # Son kullanıcı mesajını al
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break
    
    if not last_user_message:
        return {"next_agent": "end", "current_state": ConversationState.IDLE}
    
    # ─────────────────────────────────────────────────────────────
    # ESCALATION CHECK (Sentiment-based)
    # ─────────────────────────────────────────────────────────────
    """
    # Hızlı kontrol: Açık insan talebi var mı?
    if await quick_escalation_check(last_user_message):
        logger.info("🚨 [SUPERVISOR] Explicit escalation request detected")
        return {
            "next_agent": "escalation",
            "current_state": ConversationState.ESCALATION
        }
    # Detaylı analiz: Frustration/anger var mı?
    conversation_context = "\n".join([
        f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content}"
        for m in messages[-5:]
        if hasattr(m, 'content')
    ])
    # ACTION veya SHARPENING sırasında sentiment kontrolü
    if (
        current_state == ConversationState.ACTION or  # Action sırasında
        current_state == ConversationState.SHARPENING  # Sharpening sırasında
    ):
        escalation_result = await analyze_escalation_need(last_user_message, conversation_context)
        if escalation_result.get("should_escalate"):
            logger.info(f"🚨 [SUPERVISOR] Escalation needed: {escalation_result.get('reason')}")
            return {
                "next_agent": "escalation",
                "current_state": ConversationState.ESCALATION,
                "escalation_reason": escalation_result.get("reason")
            }
    """
    # ─────────────────────────────────────────────────────────────
    # NORMAL ROUTING
    # ─────────────────────────────────────────────────────────────
    
    # IDLE (ilk mesaj)
    if current_state == ConversationState.IDLE:
        travel_context = state.get("travel_context") or create_empty_travel_context()
        
        # Intent analizi
        system_prompt = f"""You are a travel intent classifier. Analyze the user's message and determine their intent.

User message: "{last_user_message}"

Classify into ONE of these categories:

1. **PLANNING**: User wants to plan a trip but lacks key details (destination, dates, travelers).
   Example: "I want to go on vacation", "Planning a trip next month"
   
2. **REACTIVE**: User has enough info to search immediately (has destination, date).
   Example: "Book me a flight to Paris on March 15th"
   
3. **INFO**: User is asking a factual question (policies, general info).
   Example: "What's your cancellation policy?", "Do you accept credit cards?"

Also determine if user has provided:
- Destination: yes/no
- Dates: yes/no
- Number of travelers: yes/no

Return JSON:
{{
    "category": "PLANNING" | "REACTIVE" | "INFO",
    "has_destination": true/false,
    "has_dates": true/false,
    "has_travelers": true/false
}}
"""
        
        messages_for_intent = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_user_message)
        ]
        
        response = await llm.ainvoke(messages_for_intent)
        
        try:
            result = json.loads(response.content.strip())
            category = result.get("category", "PLANNING")
            has_details = (
                result.get("has_destination", False) and
                result.get("has_dates", False)
            )
            
            logger.info(f"🎯 [SUPERVISOR] Intent: {category}, has_details: {has_details}")
            
            # REACTIVE: Direkt action'a git
            if category == "REACTIVE" and has_details:
                return {
                    "next_agent": "action",
                    "current_state": ConversationState.ACTION,
                    "intent_category": "REACTIVE",
                    "plan_ready": True  # ← ÖNEMLİ: Plan hazır!
                }
            
            # INFO: Info agent'a git
            elif category == "INFO":
                return {
                    "next_agent": "info",
                    "current_state": ConversationState.INFO,
                    "intent_category": "INFO"
                }
            
            # PLANNING: Sharpener'a git
            else:
                return {
                    "next_agent": "sharpener",
                    "current_state": ConversationState.SHARPENING,
                    "intent_category": "PLANNING"
                }
                
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Intent parse error: {e}")
            return {
                "next_agent": "sharpener",
                "current_state": ConversationState.SHARPENING
            }
    
    # SHARPENING
    elif current_state == ConversationState.SHARPENING:
        if state.get("plan_ready"):
            logger.info("✅ [SUPERVISOR] Plan ready, routing to ACTION")
            return {
                "next_agent": "action",
                "current_state": ConversationState.ACTION,
                "plan_ready": True
            }
        else:
            return {
                "next_agent": "sharpener",
                "current_state": ConversationState.SHARPENING
            }
    
    # READY_FOR_ACTION
    elif current_state == ConversationState.READY_FOR_ACTION:
        return {
            "next_agent": "action",
            "current_state": ConversationState.ACTION
        }
    
    # ACTION
    elif current_state == ConversationState.ACTION:
        completed_tasks = state.get("completed_tasks", [])
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        
        # ═══════════════════════════════════════════════════════════
        # CRITICAL FIX: Check if results were presented
        # ═══════════════════════════════════════════════════════════
        if "results_presented" in completed_tasks:
            # Results shown to user, wait for their input
            logger.info("📋 [SUPERVISOR] Results presented, waiting for user selection")
            return {
                "next_agent": "end",
                "current_state": ConversationState.ACTION
            }
        
        # Tool sonuçları var mı kontrol et
        has_tool_results = False
        for msg in reversed(messages[-5:]):
            if hasattr(msg, 'type') and msg.type == 'tool':
                has_tool_results = True
                break
            if msg.__class__.__name__ == 'ToolMessage':
                has_tool_results = True
                break
        
        # AI içerik var mı kontrol et
        last_ai_has_content = False
        if last_message and hasattr(last_message, 'content') and last_message.content:
            if not (hasattr(last_message, 'tool_calls') and last_message.tool_calls):
                last_ai_has_content = True
        
        if has_tool_results and not last_ai_has_content:
            logger.info("📊 [SUPERVISOR] Tool results received, routing to ACTION for formatting")
            return {
                "next_agent": "action",
                "current_state": ConversationState.ACTION
            }
        
        if "action_completed" in completed_tasks and last_ai_has_content:
            logger.info("✅ [SUPERVISOR] Action completed with results, ending")
            return {
                "next_agent": "end",
                "current_state": ConversationState.COMPLETED
            }
        
        return {
            "next_agent": "action",
            "current_state": ConversationState.ACTION
        }
    
    # INFO
    elif current_state == ConversationState.INFO:
        # Info sorusu cevaplandı mı?
        prev_state = state.get("previous_state", ConversationState.IDLE)
        
        if prev_state == ConversationState.SHARPENING:
            return {"next_agent": "sharpener", "current_state": ConversationState.SHARPENING}
        elif prev_state == ConversationState.ACTION:
            return {"next_agent": "action", "current_state": ConversationState.ACTION}
        else:
            return {"next_agent": "end", "current_state": ConversationState.IDLE}
    
    # COMPLETED
    elif current_state == ConversationState.COMPLETED:
        if "another" in last_user_message.lower() or "else" in last_user_message.lower():
            logger.info("✅ [SUPERVISOR] User confirmed, routing to ACTION")
            return {
                "next_agent": "action",
                "current_state": ConversationState.ACTION,
                "completed_tasks": []  # Reset
            }
        else:
            return {"next_agent": "end", "current_state": ConversationState.COMPLETED}
    
    # ESCALATION
    elif current_state == ConversationState.ESCALATION:
        return {
            "next_agent": "escalation",
            "current_state": ConversationState.ESCALATION
        }
    
    # Fallback
    return {"next_agent": "end", "current_state": current_state}