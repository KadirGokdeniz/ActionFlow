"""
ActionFlow API - WhatsApp Routes (Twilio)
Handles incoming WhatsApp messages via Twilio Webhook.
"""

import uuid
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db, Conversation, Message, User, ConversationStatus, ChannelType
from app.core.orchestrator import chat, get_graph, AgentState
from app.core.redis import get_conversation_state, set_conversation_state

from twilio.twiml.messaging_response import MessagingResponse
from langchain_core.messages import HumanMessage, AIMessage

# ═══════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════

logger = logging.getLogger("ActionFlow-WhatsApp")

# ═══════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def get_or_create_user_by_phone(db: AsyncSession, phone: str) -> User:
    """Find user by phone or create new one"""
    # Normalize phone (strip whatsapp: prefix if exists, though we store full string usually)
    # Twilio sends 'whatsapp:+1234567890'
    
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    
    if not user:
        logger.info(f"Creating new user for phone: {phone}")
        user = User(
            id=str(uuid.uuid4()),
            phone=phone,
            first_name="WhatsApp User",  # Placeholder, can update via ProfileName
            tier="standard"
        )
        db.add(user)
        await db.flush()
        
    return user

async def get_active_conversation(db: AsyncSession, user_id: str) -> tuple[Conversation, bool]:
    """Get active whatsapp conversation or create new"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .where(Conversation.status == ConversationStatus.ACTIVE)
        .where(Conversation.channel == ChannelType.WHATSAPP)
        .order_by(desc(Conversation.updated_at))
        .limit(1)
    )
    conversation = result.scalar_one_or_none()
    
    if conversation:
        return conversation, False
    
    # Create new
    logger.info(f"Starting new WhatsApp conversation for user {user_id}")
    new_conv = Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        status=ConversationStatus.ACTIVE,
        channel=ChannelType.WHATSAPP,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_conv)
    await db.flush()
    return new_conv, True

async def save_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    agent_type: Optional[str] = None
) -> Message:
    """Save message to DB"""
    message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        agent_type=agent_type,
        created_at=datetime.utcnow()
    )
    db.add(message)
    await db.flush()  # We commit at the end of request
    return message

async def load_history(db: AsyncSession, conversation_id: str) -> List[HumanMessage | AIMessage]:
    """Load conversation history"""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    lc_messages = []
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
    return lc_messages

# ═══════════════════════════════════════════════════════════════════
# WEBHOOK ENDPOINT
# ═══════════════════════════════════════════════════════════════════

@router.post("/webhook")
async def handle_whatsapp_incoming(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    ProfileName: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Twilio Webhook Handler
    Receives incoming WhatsApp messages.
    """
    logger.info(f"📩 WhatsApp Message from {From}: {Body}")
    
    try:
        # 1. Kimlik Doğrulama / Kullanıcı Eşleştirme
        user = await get_or_create_user_by_phone(db, From)
        
        # ProfileName varsa güncelle
        if ProfileName and user.first_name == "WhatsApp User":
            user.first_name = ProfileName
            db.add(user)
        
        # 2. Konuşma Yönetimi
        conversation, is_new = await get_active_conversation(db, user.id)
        
        # 3. Mesajı Kaydet (User)
        await save_message(db, conversation.id, "user", Body)
        
        # 4. Redis State Kontrolü
        cached_state = await get_conversation_state(conversation.id)
        
        travel_context = None
        current_state = None
        plan_ready = False
        sharpening_turns = 0
        action_turns = 0
        
        if cached_state:
            travel_context = cached_state.get("travel_context")
            current_state = cached_state.get("current_state")
            plan_ready = cached_state.get("plan_ready", False)
            sharpening_turns = cached_state.get("sharpening_turns", 0)
            action_turns = cached_state.get("action_turns", 0)
        elif not is_new:
            # Fallback DB
            travel_context = conversation.travel_context
            
        # 5. Geçmişi Yükle
        history = []
        if not is_new:
            history = await load_history(db, conversation.id)
            # Remove the message we just added efficiently? 
            # Actually load_history fetches all. We just added the user message.
            # Orchestrator usually expects history NOT including the current turn?
            # In chat_routes, it passes history[:-1]. 
            # Here we fetched from DB, which INCLUDES the message we just saved if flush worked.
            # Yes, await db.flush() makes it visible in transaction.
            # So history[-1] is the current message.
            if history:
                history = history[:-1]

        # 6. AI Yanıtı Üret
        result = await chat(
            message=Body,
            customer_id=user.id,
            conversation_history=history,
            travel_context=travel_context,
            current_state=current_state,
            plan_ready=plan_ready,
            sharpening_turns=sharpening_turns,
            action_turns=action_turns
        )
        
        response_text = result["response"]
        updated_state = result["state"]
        
        # 7. Yanıtı Kaydet (AI)
        await save_message(
            db, 
            conversation.id, 
            "assistant", 
            response_text,
            agent_type=updated_state.get("current_state")
        )
        
        # 8. State'i Güncelle (Redis + DB)
        state_to_cache = {
            "travel_context": updated_state.get("travel_context"),
            "current_state": updated_state.get("current_state"),
            "plan_ready": updated_state.get("plan_ready", False),
            "sharpening_turns": updated_state.get("sharpening_turns", 0),
            "action_turns": updated_state.get("action_turns", 0),
            "intent_category": updated_state.get("intent_category"),
            "completed_tasks": updated_state.get("completed_tasks", [])
        }
        await set_conversation_state(conversation.id, state_to_cache)
        
        if updated_state.get("travel_context"):
            conversation.travel_context = updated_state["travel_context"]
        conversation.updated_at = datetime.utcnow()
        
        await db.commit()
        
        # 9. Twilio Yanıtı (TwiML)
        twiml_resp = MessagingResponse()
        twiml_resp.message(response_text)
        
        return Response(content=str(twiml_resp), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"WhatsApp Error: {e}", exc_info=True)
        # Hata durumunda kullanıcıya bilgi ver
        twiml_resp = MessagingResponse()
        twiml_resp.message("I'm sorry, I encountered an error creating your response. Please try again.")
        return Response(content=str(twiml_resp), media_type="application/xml")
