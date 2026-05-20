# -*- coding: utf-8 -*-
import uuid
import logging
from datetime import datetime
from typing import Optional, List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, AIMessage

# Pydantic ve FastAPI importlarını ekledik
from fastapi import APIRouter, Depends
from pydantic import BaseModel 

from app.core.database import Conversation, Message, ConversationStatus

logger = logging.getLogger("ActionFlow-ChatService")


def detect_english(text: str) -> bool:
    """Check if text is primarily English"""
    english_words = ["the", "is", "are", "you", "your", "have", "what", "where", "when", 
                     "great", "now", "could", "share", "specific", "trip", "budget",
                     "and", "for", "kind", "of", "destination", "mind", "dreaming"]
    word_count = sum(1 for word in english_words if word.lower() in text.lower())
    
    turkish_chars = ["ı", "ğ", "ü", "ş", "ö", "ç", "İ", "Ğ", "Ü", "Ş", "Ö", "Ç"]
    has_turkish = any(char in text for char in turkish_chars)
    
    print(f"DEBUG: word_count={word_count}, has_turkish={has_turkish}, text={text[:50]}")
    
    return word_count >= 2 and not has_turkish

async def force_translate_to_turkish(text: str) -> str:
    """Force translate response to Turkish using LLM"""
    from app.core.llm import llm
    from langchain_core.messages import SystemMessage
    
    response = await llm.ainvoke([
        SystemMessage(content=f"Translate this to Turkish, keep the same tone: {text}")
    ])
    return response.content

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
) -> list:
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

