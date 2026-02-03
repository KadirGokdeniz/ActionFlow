"""
ActionFlow AI - Database Models & Connection
PostgreSQL + pgvector for conversations, bookings, and policy RAG

Setup: pip install sqlalchemy asyncpg pgvector python-dotenv
"""

import os
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column, String, Integer, Float, Text, Boolean, DateTime, JSON, ForeignKey,
    Enum as SQLEnum, Index, create_engine, text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ═══════════════════════════════════════════════════════════════════
# DATABASE URL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

# URL'leri async ve sync için ayır
if DATABASE_URL.startswith("postgresql+asyncpg"):
    ASYNC_DATABASE_URL = DATABASE_URL
    SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
else:
    SYNC_DATABASE_URL = DATABASE_URL
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# ═══════════════════════════════════════════════════════════════════
# BASE & PGVECTOR SETUP
# ═══════════════════════════════════════════════════════════════════

Base = declarative_base()

# pgvector import - optional, gracefully handle if not installed
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    Vector = None
    PGVECTOR_AVAILABLE = False
    print("Warning: pgvector not installed. Vector search disabled.")


# ═══════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════

class ChannelType(str, Enum):
    WEB = "web"
    WHATSAPP = "whatsapp"
    VOICE = "voice"
    API = "api"


class BookingType(str, Enum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    ACTIVITY = "activity"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    FAILED = "failed"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"


# ═══════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════

class User(Base):
    """User profiles - travelers using the system"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)  # UUID
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(50), unique=True, nullable=True)  # WhatsApp: whatsapp:+1234567890
    first_name = Column(String(100))
    last_name = Column(String(100))
    preferred_language = Column(String(10), default="en")
    tier = Column(String(20), default="standard")  # standard, premium, vip
    preferences = Column(JSON, default=dict)  # preferences, passport info, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user")
    bookings = relationship("Booking", back_populates="user")


class Conversation(Base):
    """Conversation sessions with transcript and embeddings"""
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    channel = Column(
        SQLEnum(ChannelType, name="channel_type", native_enum=False),
        default=ChannelType.WEB
    )
    status = Column(
        SQLEnum(ConversationStatus, name="conversation_status", native_enum=False),
        default=ConversationStatus.ACTIVE
    )
    
    # Content
    transcript = Column(Text)  # Full conversation text
    summary = Column(Text)     # AI-generated summary
    
    # Orchestrator state persistence (NEW - for multi-turn conversations)
    travel_context = Column(JSON, nullable=True)  # TravelContext from orchestrator
    agent_state = Column(JSON, nullable=True)     # Current state, plan_ready, etc.
    
    # Voice-specific (nullable - only for voice channel)
    audio_ref = Column(String(500), nullable=True)  # S3/MinIO path - future use
    stt_confidence = Column(Float, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Embedding for semantic search (requires pgvector)
    transcript_embedding = Column(Vector(1536), nullable=True) if PGVECTOR_AVAILABLE else Column(Text, nullable=True)
    
    # Agent routing info
    intent = Column(String(50))           # booking, cancellation, inquiry, etc.
    urgency_score = Column(Integer)       # 1-5
    escalated_to = Column(String(100), nullable=True)  # human agent name/id
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    bookings = relationship("Booking", back_populates="conversation")


class Message(Base):
    """Individual messages within a conversation"""
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id"))
    
    role = Column(String(20))  # user, assistant, system
    content = Column(Text)
    
    # Voice-specific
    is_voice = Column(Boolean, default=False)
    audio_ref = Column(String(500), nullable=True)
    
    # Agent info
    agent_type = Column(String(50), nullable=True)  # supervisor, info, action, escalation
    tool_calls = Column(JSON, nullable=True)        # MCP tool invocations
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class Booking(Base):
    """Travel bookings - flights, hotels, activities"""
    __tablename__ = "bookings"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=True)
    
    # FIX: Doğru enum ve default değerler
    booking_type = Column(
        SQLEnum(BookingType, name="booking_type", native_enum=False),
        default=BookingType.FLIGHT
    )
    status = Column(
        SQLEnum(BookingStatus, name="booking_status", native_enum=False),
        default=BookingStatus.PENDING
    )
    
    # External references
    external_id = Column(String(100))      # Amadeus booking ID
    pnr = Column(String(10), nullable=True)  # For flights
    
    # Booking details
    details = Column(JSON)  # Full booking data from Amadeus
    
    # Pricing
    currency = Column(String(3), default="EUR")
    total_amount = Column(Float)
    refund_amount = Column(Float, nullable=True)
    
    # Dates
    travel_date = Column(DateTime)
    booked_at = Column(DateTime, default=datetime.utcnow)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    conversation = relationship("Conversation", back_populates="bookings")


class Policy(Base):
    """Cancellation policies, refund rules, FAQs for RAG"""
    __tablename__ = "policies"
    
    id = Column(String(36), primary_key=True)
    
    # Categorization
    category = Column(String(50))   # cancellation, refund, baggage, check-in, etc.
    provider = Column(String(100))  # airline/hotel name, or "general"
    
    # Content
    title = Column(String(255))
    content = Column(Text)
    
    # Embedding for semantic search (requires pgvector)
    content_embedding = Column(Vector(1536), nullable=True) if PGVECTOR_AVAILABLE else Column(Text, nullable=True)
    
    # Metadata
    effective_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    source_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════
# INDEXES
# ═══════════════════════════════════════════════════════════════════

Index("ix_conversations_user", Conversation.user_id)
Index("ix_conversations_status", Conversation.status)
Index("ix_bookings_user", Booking.user_id)
Index("ix_bookings_status", Booking.status)
Index("ix_policies_category", Policy.category)


# ═══════════════════════════════════════════════════════════════════
# DATABASE ENGINES & SESSION
# ═══════════════════════════════════════════════════════════════════

# Lazy initialization için global değişkenler
_async_engine = None
_async_session_maker = None
_sync_engine = None


def get_sync_engine():
    """Sync engine döndürür (Alembic migrations için)"""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)
    return _sync_engine


def get_async_engine():
    """Async engine döndürür"""
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            ASYNC_DATABASE_URL,
            echo=False,  # Production'da False olmalı
            pool_pre_ping=True,  # Connection health check
            pool_size=5,
            max_overflow=10
        )
    return _async_engine


def get_async_session_maker():
    """Async session maker döndürür"""
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_async_engine()
        _async_session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    return _async_session_maker


async def get_db():
    """FastAPI dependency - async session yield eder"""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Database'i initialize eder:
    1. pgvector extension'ı oluşturur
    2. Tüm tabloları oluşturur
    """
    engine = get_async_engine()
    
    async with engine.begin() as conn:
        # pgvector extension'ı oluştur (varsa atla)
        if PGVECTOR_AVAILABLE:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("✅ pgvector extension ready")
        
        # Tabloları oluştur
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created")


async def close_db():
    """Database bağlantılarını kapat"""
    global _async_engine, _async_session_maker
    
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_maker = None
        print("✅ Database connections closed")


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def vector_search(
    session: AsyncSession,
    table,
    embedding_column,
    query_embedding: list,
    limit: int = 5
):
    """
    Semantic similarity search using pgvector
    
    Args:
        session: AsyncSession instance
        table: SQLAlchemy model class (e.g., Policy, Conversation)
        embedding_column: Column to search (e.g., Policy.content_embedding)
        query_embedding: Query vector (list of floats)
        limit: Max results to return
    
    Returns:
        List of matching records ordered by similarity
    """
    from sqlalchemy import select
    
    if not PGVECTOR_AVAILABLE:
        raise RuntimeError("pgvector is not installed. Run: pip install pgvector")
    
    stmt = (
        select(table)
        .order_by(embedding_column.cosine_distance(query_embedding))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_embedding(text: str, client=None) -> list:
    """
    OpenAI embedding oluşturur (RAG için)
    
    Args:
        text: Embed edilecek metin
        client: OpenAI client (optional, yoksa yeni oluşturur)
    
    Returns:
        1536 boyutlu embedding vector
    """
    from openai import AsyncOpenAI
    
    if client is None:
        client = AsyncOpenAI()
    
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


# ═══════════════════════════════════════════════════════════════════
# POLICY SEARCH (RAG Helper)
# ═══════════════════════════════════════════════════════════════════

async def search_policies_by_text(
    session: AsyncSession,
    query: str,
    category: str = None,
    limit: int = 5
) -> list:
    """
    Metin sorgusuyla policy arar (semantic search)
    
    Args:
        session: Database session
        query: Arama metni
        category: Opsiyonel kategori filtresi
        limit: Max sonuç sayısı
    
    Returns:
        İlgili Policy listesi
    """
    from sqlalchemy import select, and_
    
    # Embedding oluştur
    query_embedding = await get_embedding(query)
    
    # Base query
    stmt = select(Policy)
    
    # Kategori filtresi
    if category:
        stmt = stmt.where(Policy.category == category)
    
    # Similarity search
    stmt = (
        stmt
        .order_by(Policy.content_embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    
    result = await session.execute(stmt)
    return result.scalars().all()