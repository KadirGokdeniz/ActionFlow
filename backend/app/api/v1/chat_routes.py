"""
ActionFlow API - Chat Routes
"""
import time
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, AIMessage

from app.core.database import get_db, Conversation, Message, ConversationStatus
from app.core.orchestrator import chat, mcp_client
from app.core.redis import get_conversation_state, set_conversation_state
from app.services.chat_service import (
    detect_english, force_translate_to_turkish,
    get_or_create_conversation, save_message, load_conversation_messages,
    restore_cached_state, build_state_to_cache,
)

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger("ActionFlow-ChatRoutes")


# ?? Models ????????????????????????????????????????????????????????????????????

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    customer_id: Optional[str] = None
    conversation_id: Optional[str] = None
    language: Optional[str] = Field(default="en")

    model_config = ConfigDict(json_schema_extra={"example": {
        "message": "Yarin IST'den Amsterdam'a ucus var mi?",
        "customer_id": "user123",
        "conversation_id": None,
        "language": "auto"
    }})


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime
    agent_type: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    intent: Optional[str] = None
    agent_used: Optional[str] = None
    current_state: Optional[str] = None
    tool_calls: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None
    processing_time_ms: Optional[int] = None

    model_config = ConfigDict(json_schema_extra={"example": {
        "conversation_id": "conv_abc123",
        "message": "IST-AMS icin yarin 3 ucus buldum...",
        "intent": "flight_search",
        "agent_used": "action",
        "current_state": "ACTION",
        "processing_time_ms": 1250
    }})


class ConversationHistory(BaseModel):
    conversation_id: str
    customer_id: Optional[str]
    status: str
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime


# ?? Main endpoint ?????????????????????????????????????????????????????????????

@router.post("", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send a message and receive an AI response."""
    start_time = time.time()
    try:
        # 1. Load cached state from Redis
        cached_state = None
        if request.conversation_id:
            cached_state = await get_conversation_state(request.conversation_id)
            if cached_state:
                logger.info(f"Redis cache HIT: conv={request.conversation_id}, "
                            f"state={cached_state.get('current_state')}")

        # 2. Get or create conversation
        conversation, is_new = await get_or_create_conversation(
            db, request.conversation_id, request.customer_id
        )
        logger.info(f"Chat request: conv={conversation.id}, new={is_new}")

        # 3. Save user message
        await save_message(db, conversation.id, role="user", content=request.message)

        # 4. Load message history (exclude the message just saved)
        history = []
        if not is_new:
            history = await load_conversation_messages(db, conversation.id)
            if history:
                history = history[:-1]

        # 5. Restore state from cache (or DB fallback)
        state = restore_cached_state(cached_state, conversation, is_new)

        # 6. Call orchestrator
        customer_id = request.customer_id or conversation.user_id or "anonymous"
        result = await chat(
            message=request.message,
            customer_id=customer_id,
            conversation_history=history,
            **state
        )

        response_text = result["response"]
        updated_state = result["state"]
        suggestions = result.get("suggestions", [])

        # 7. Translate if requested
        request_language = request.language or "en"
        if request_language == "tr" and detect_english(response_text):
            logger.info(f"Translating response to Turkish")
            response_text = await force_translate_to_turkish(response_text)

        # 8. Save assistant message
        await save_message(
            db, conversation.id,
            role="assistant",
            content=response_text,
            agent_type=updated_state.get("current_state", "unknown")
        )

        # 9. Persist state to Redis + DB
        state_to_cache = build_state_to_cache(updated_state, request_language)
        await set_conversation_state(conversation.id, state_to_cache)
        logger.info(f"State saved: {state_to_cache.get('current_state')}")

        if updated_state.get("travel_context"):
            conversation.travel_context = updated_state["travel_context"]
        conversation.updated_at = datetime.utcnow()
        await db.commit()

        # 10. Return response
        return ChatResponse(
            conversation_id=conversation.id,
            message=response_text,
            intent=updated_state.get("intent_category"),
            agent_used=updated_state.get("current_state"),
            current_state=updated_state.get("current_state"),
            suggestions=suggestions,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ?? Other endpoints ???????????????????????????????????????????????????????????

@router.get("/history/{conversation_id}", response_model=ConversationHistory)
async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get conversation history."""
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
    """Delete a conversation and its Redis state."""
    from sqlalchemy import select, delete
    from app.core.redis import delete_conversation_state

    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await delete_conversation_state(conversation_id)
    await db.execute(delete(Message).where(Message.conversation_id == conversation_id))
    await db.delete(conversation)
    await db.commit()

    return {"status": "deleted", "conversation_id": conversation_id}


@router.get("/health")
async def chat_health():
    """Chat service health check."""
    try:
        tools = await mcp_client.list_tools()
        mcp_status = "connected"
        tool_count = len(tools)
    except Exception as e:
        mcp_status = f"error: {str(e)}"
        tool_count = 0

    return {
        "status": "healthy",
        "mcp": {"status": mcp_status, "tools_available": tool_count}
    }


@router.post("/stream")
async def send_message_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Streaming response (SSE)."""
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
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )
