"""
ActionFlow API - Chat Routes (FIXED)
State persistence düzeltmesi uygulandı.

DEĞİŞİKLİKLER:
1. Redis'te artık sadece travel_context değil, tüm conversation_state tutuluyor
2. current_state, plan_ready, sharpening_turns gibi değerler korunuyor
3. Orchestrator'dan dönen state bilgisi tam olarak kaydediliyor
"""

import uuid
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, Conversation, Message, User, ConversationStatus
from app.core.orchestrator import chat, get_graph, mcp_client, AgentState, ConversationState
from app.core.redis import get_conversation_state, set_conversation_state

from langchain_core.messages import HumanMessage, AIMessage

def detect_english(text: str) -> bool:
    """Check if text is primarily English"""
    # Daha fazla kelime kontrolü
    english_words = ["the", "is", "are", "you", "your", "have", "what", "where", "when", 
                     "great", "now", "could", "share", "specific", "trip", "budget",
                     "and", "for", "kind", "of", "destination", "mind", "dreaming"]
    word_count = sum(1 for word in english_words if word.lower() in text.lower())
    
    # Türkçe karakter yoksa muhtemelen İngilizce
    turkish_chars = ["ı", "ğ", "ü", "ş", "ö", "ç", "İ", "Ğ", "Ü", "Ş", "Ö", "Ç"]
    has_turkish = any(char in text for char in turkish_chars)
    
    # Debug log ekle
    print(f"DEBUG: word_count={word_count}, has_turkish={has_turkish}, text={text[:50]}")
    
    return word_count >= 2 and not has_turkish  # Eşiği düşür

async def force_translate_to_turkish(text: str) -> str:
    """Force translate response to Turkish using LLM"""
    from app.core.llm import llm
    from langchain_core.messages import SystemMessage
    
    response = await llm.ainvoke([
        SystemMessage(content=f"Translate this to Turkish, keep the same tone: {text}")
    ])
    return response.content

# ═══════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════

logger = logging.getLogger("ActionFlow-ChatAPI")

# ═══════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/chat", tags=["Chat"])


# ═══════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """Chat isteği"""
    message: str = Field(..., min_length=1, max_length=4000, description="Kullanıcı mesajı")
    customer_id: Optional[str] = Field(default=None, description="Müşteri ID")
    conversation_id: Optional[str] = Field(default=None, description="Mevcut konuşma ID (devam etmek için)")
    language: Optional[str] = Field(default="en", description="Tercih edilen dil: tr, en, auto")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Yarın IST'den Amsterdam'a uçuş var mı?",
                "customer_id": "user123",
                "conversation_id": None,
                "language": "auto"
            }
        }


class ChatMessage(BaseModel):
    """Tek bir mesaj"""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    agent_type: Optional[str] = None  # supervisor, info, action


class ChatResponse(BaseModel):
    """Chat yanıtı"""
    conversation_id: str
    message: str
    intent: Optional[str] = None
    agent_used: Optional[str] = None
    current_state: Optional[str] = None  # YENİ: Mevcut state bilgisi
    tool_calls: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None
    processing_time_ms: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv_abc123",
                "message": "IST-AMS için yarın 3 uçuş buldum...",
                "intent": "flight_search",
                "agent_used": "action",
                "current_state": "ACTION",
                "tool_calls": ["search_flights"],
                "suggestions": ["Morning flights", "Business class", "Direct only"],
                "processing_time_ms": 1250
            }
        }


class ConversationHistory(BaseModel):
    """Konuşma geçmişi"""
    conversation_id: str
    customer_id: Optional[str]
    status: str
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def get_or_create_conversation(
    db: AsyncSession,
    conversation_id: Optional[str],
    customer_id: Optional[str]
) -> tuple[Conversation, bool]:
    """
    Konuşma getir veya yeni oluştur
    
    Returns:
        (conversation, is_new)
    """
    from sqlalchemy import select
    
    # Mevcut konuşmayı getir
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if conversation:
            return conversation, False
    
    # Yeni konuşma oluştur
    new_conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=None,
        status=ConversationStatus.ACTIVE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_conversation)
    await db.flush()
    
    return new_conversation, True


async def save_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    agent_type: Optional[str] = None,
    tool_calls: Optional[list] = None
) -> Message:
    """Mesajı veritabanına kaydet"""
    message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        agent_type=agent_type,
        tool_calls=tool_calls,
        created_at=datetime.utcnow()
    )
    db.add(message)
    await db.flush()
    return message


async def load_conversation_messages(
    db: AsyncSession,
    conversation_id: str
) -> List[HumanMessage | AIMessage]:
    """Konuşma geçmişini LangChain mesajlarına çevir"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    langchain_messages = []
    for msg in messages:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))
    
    return langchain_messages


# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Mesaj gönder ve yanıt al
    
    - Yeni konuşma başlatır veya mevcut konuşmaya devam eder
    - Orchestrator üzerinden uygun agent'a yönlendirir
    - Mesajları veritabanına kaydeder
    - State ve travel_context'i TAMAMEN persist eder (FIX!)
    """
    import time
    start_time = time.time()
    
    try:
        # ═══════════════════════════════════════════════════════════
        # 1. REDIS'TEN MEVCUT STATE'İ AL
        # ═══════════════════════════════════════════════════════════
        cached_state = None
        if request.conversation_id:
            cached_state = await get_conversation_state(request.conversation_id)
            if cached_state:
                logger.info(f"🚀 [REDIS] Cache HIT for conv={request.conversation_id}")
                logger.info(f"   └── current_state: {cached_state.get('current_state', 'N/A')}")
        
        # Konuşma getir veya oluştur
        conversation, is_new = await get_or_create_conversation(
            db, 
            request.conversation_id,
            request.customer_id
        )
        
        logger.info(f"💬 Chat request: conv={conversation.id}, new={is_new}")
        
        # Kullanıcı mesajını kaydet
        await save_message(
            db,
            conversation.id,
            role="user",
            content=request.message
        )
        
        # Konuşma geçmişini yükle
        history = []
        if not is_new:
            history = await load_conversation_messages(db, conversation.id)
            if history:
                history = history[:-1]  # Son mesajı çıkar (az önce ekledik)
        
        # ═══════════════════════════════════════════════════════════
        # 2. CACHED STATE'İ AYIKLA
        # ═══════════════════════════════════════════════════════════
        travel_context = None
        current_state = None
        plan_ready = False
        sharpening_turns = 0
        action_turns = 0
        completed_tasks = []  # ← ADDED!
        
        if cached_state:
            travel_context = cached_state.get("travel_context")
            current_state = cached_state.get("current_state")
            plan_ready = cached_state.get("plan_ready", False)
            sharpening_turns = cached_state.get("sharpening_turns", 0)
            action_turns = cached_state.get("action_turns", 0)
            completed_tasks = cached_state.get("completed_tasks", [])  # ← ADDED!
            
            logger.info(f"   └── Restored: state={current_state}, plan_ready={plan_ready}, turns={sharpening_turns}, tasks={completed_tasks}")
        
        # DB'den fallback (Redis'te yoksa)
        if travel_context is None and not is_new:
            logger.info(f"🐢 [REDIS] Cache MISS, loading from DB")
            travel_context = conversation.travel_context
        
        # ═══════════════════════════════════════════════════════════
        # 3. ORCHESTRATOR'I ÇAĞIR (GÜNCELLENMİŞ PARAMETRELERLE)
        # ═══════════════════════════════════════════════════════════
        customer_id = request.customer_id or conversation.user_id or "anonymous"
        
        # 🔥 chat() artık full state döndürüyor
        result = await chat(
            message=request.message,
            customer_id=customer_id,
            conversation_history=history,
            travel_context=travel_context,
            current_state=current_state,
            plan_ready=plan_ready,
            sharpening_turns=sharpening_turns,
            action_turns=action_turns,
            completed_tasks=completed_tasks  # ← ADDED!
        )
        
        # Result'ı aç
        response_text = result["response"]
        updated_state = result["state"]
        suggestions = result.get("suggestions", [])
        

        request_language = request.language or "en"  # ← EKLE
        if request_language == "tr" and detect_english(response_text):  # ← DÜZELT
            logger.info(f"🔄 Translating to Turkish: {response_text[:50]}")  # ← EKLE
            response_text = await force_translate_to_turkish(response_text)
        # ═══════════════════════════════════════════════════════════
        # 4. YANITLARI KAYDET
        # ═══════════════════════════════════════════════════════════
        await save_message(
            db,
            conversation.id,
            role="assistant",
            content=response_text,
            agent_type=updated_state.get("current_state", "unknown")
        )
        
        # ═══════════════════════════════════════════════════════════
        # 5. STATE'İ REDIS'E KAYDET (TAM STATE!)
        # ═══════════════════════════════════════════════════════════
        state_to_cache = {
            "travel_context": updated_state.get("travel_context"),
            "current_state": updated_state.get("current_state"),
            "plan_ready": updated_state.get("plan_ready", False),
            "sharpening_turns": updated_state.get("sharpening_turns", 0),
            "action_turns": updated_state.get("action_turns", 0),
            "intent_category": updated_state.get("intent_category"),
            "completed_tasks": updated_state.get("completed_tasks", []),
            "language": request_language  # ← EKLE
        }
        
        await set_conversation_state(conversation.id, state_to_cache)
        logger.info(f"💾 [REDIS] State saved: {state_to_cache.get('current_state')}")
        
        # DB'ye de travel_context kaydet (backup)
        if updated_state.get("travel_context"):
            conversation.travel_context = updated_state["travel_context"]
        
        conversation.updated_at = datetime.utcnow()
        await db.commit()
        
        # ═══════════════════════════════════════════════════════════
        # 6. RESPONSE
        # ═══════════════════════════════════════════════════════════
        processing_time = int((time.time() - start_time) * 1000)
        
        return ChatResponse(
            conversation_id=conversation.id,
            message=response_text,
            intent=updated_state.get("intent_category"),
            agent_used=updated_state.get("current_state"),
            current_state=updated_state.get("current_state"),
            tool_calls=None,  # TODO: Orchestrator'dan al
            suggestions=suggestions,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{conversation_id}", response_model=ConversationHistory)
async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Konuşma geçmişini getir"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    return ConversationHistory(
        conversation_id=conversation.id,
        customer_id=conversation.user_id,
        status=conversation.status.value if conversation.status else "active",
        messages=[
            ChatMessage(
                role=msg.role,
                content=msg.content,
                timestamp=msg.created_at,
                agent_type=msg.agent_type
            )
            for msg in messages
        ],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at
    )


@router.delete("/history/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Konuşmayı sil"""
    from sqlalchemy import select, delete
    from app.core.redis import delete_conversation_state
    
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Redis'ten de sil
    await delete_conversation_state(conversation_id)
    
    # Mesajları sil
    await db.execute(
        delete(Message).where(Message.conversation_id == conversation_id)
    )
    
    # Konuşmayı sil
    await db.delete(conversation)
    await db.commit()
    
    return {"status": "deleted", "conversation_id": conversation_id}


@router.get("/health")
async def chat_health():
    """Chat servisi sağlık kontrolü"""
    try:
        tools = await mcp_client.list_tools()
        mcp_status = "connected"
        tool_count = len(tools)
    except Exception as e:
        mcp_status = f"error: {str(e)}"
        tool_count = 0
    
    return {
        "status": "healthy",
        "mcp": {
            "status": mcp_status,
            "tools_available": tool_count
        }
    }


# ═══════════════════════════════════════════════════════════════════
# STREAMING ENDPOINT
# ═══════════════════════════════════════════════════════════════════

@router.post("/stream")
async def send_message_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Streaming yanıt (SSE)"""
    import json
    
    async def generate():
        try:
            result = await chat(
                message=request.message,
                customer_id=request.customer_id or "anonymous"
            )
            
            response_text = result["response"]
            words = response_text.split()
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )