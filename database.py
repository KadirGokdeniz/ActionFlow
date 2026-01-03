"""
ActionFlow AI - Database Models & Connection
PostgreSQL + pgvector for conversations, bookings, and policy RAG

Setup: pip install sqlalchemy asyncpg pgvector python-dotenv psycopg2-binary
"""

from sqlalchemy import (
    Column, String, Integer, Float, Text, Boolean, DateTime, JSON, ForeignKey,
    Enum as SQLEnum, Index, create_engine, text
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from enum import Enum
import os

# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

# Sync URL for migrations and init scripts
SYNC_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://actionflow:dev123@localhost:5432/actionflow"
).replace("+asyncpg", "")

# Async URL for FastAPI runtime
ASYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

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
    phone = Column(String(20), unique=True, nullable=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    preferred_language = Column(String(10), default="en")
    tier = Column(String(20), default="standard")  # standard, premium, vip
    preferences = Column(JSON, default={})  # preferences, passport info, etc.
    
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
    channel = Column(SQLEnum(ChannelType), default=ChannelType.WEB)
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE)
    
    # Content
    transcript = Column(Text)  # Full conversation text
    summary = Column(Text)     # AI-generated summary
    
    # Voice-specific (nullable - only for voice channel)
    audio_ref = Column(String(500), nullable=True)  # S3/MinIO path - future use
    stt_confidence = Column(Float, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Embedding for semantic search - Text fallback if pgvector not available
    if PGVECTOR_AVAILABLE:
        transcript_embedding = Column(Vector(1536), nullable=True)
    else:
        transcript_embedding = Column(Text, nullable=True)
    
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
    
    booking_type = Column(SQLEnum(BookingType))
    status = Column(SQLEnum(BookingStatus), default=BookingStatus.PENDING)
    
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
    
    # Embedding for semantic search - Text fallback if pgvector not available
    if PGVECTOR_AVAILABLE:
        content_embedding = Column(Vector(1536), nullable=True)
    else:
        content_embedding = Column(Text, nullable=True)
    
    # Metadata
    effective_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    source_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════
# INDEXES
# ═══════════════════════════════════════════════════════════════════

# Standard indexes
Index("ix_conversations_user", Conversation.user_id)
Index("ix_conversations_status", Conversation.status)
Index("ix_bookings_user", Booking.user_id)
Index("ix_bookings_status", Booking.status)
Index("ix_policies_category", Policy.category)


# ═══════════════════════════════════════════════════════════════════
# DATABASE CONNECTION
# ═══════════════════════════════════════════════════════════════════

# Global variables for lazy initialization
_async_engine = None
_async_session_maker = None

# Export alias for backward compatibility (will be set when engine initializes)
async_session = None


def get_sync_engine():
    """Get synchronous engine for migrations and init scripts"""
    return create_engine(SYNC_DATABASE_URL, echo=False)


def get_async_engine():
    """Get async engine for FastAPI runtime"""
    global _async_engine, _async_session_maker, async_session
    
    if _async_engine is None:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        _async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
        _async_session_maker = async_sessionmaker(_async_engine, class_=AsyncSession, expire_on_commit=False)
        async_session = _async_session_maker  # Set the export alias
    
    return _async_engine


async def get_db():
    """Dependency for FastAPI endpoints"""
    get_async_engine()  # Ensure engine is initialized
    async with _async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables (async version for FastAPI startup)"""
    engine = get_async_engine()
    async with engine.begin() as conn:
        # Create pgvector extension (use text() for raw SQL)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def vector_search(session, table, embedding_column, query_embedding, limit: int = 5):
    """
    Semantic similarity search using pgvector
    
    Usage:
        results = await vector_search(session, Policy, Policy.content_embedding, query_emb, limit=5)
    """
    from sqlalchemy import select
    
    if not PGVECTOR_AVAILABLE:
        raise RuntimeError("pgvector is not installed. Run: pip install pgvector")
    
    # Cosine distance search
    stmt = (
        select(table)
        .order_by(embedding_column.cosine_distance(query_embedding))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()