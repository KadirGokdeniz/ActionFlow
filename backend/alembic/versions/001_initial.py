"""Initial migration - Create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-16

Creates:
- users
- conversations
- messages
- bookings
- policies

With pgvector extension for semantic search.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # ─────────────── USERS ───────────────
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=True),
        sa.Column('phone', sa.String(20), unique=True, nullable=True),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('preferred_language', sa.String(10), default='en'),
        sa.Column('tier', sa.String(20), default='standard'),
        sa.Column('preferences', sa.JSON, default=dict),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # ─────────────── CONVERSATIONS ───────────────
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('channel', sa.String(20), default='web'),  # web, whatsapp, voice, api
        sa.Column('status', sa.String(20), default='active'),  # active, completed, escalated
        sa.Column('transcript', sa.Text, nullable=True),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('audio_ref', sa.String(500), nullable=True),
        sa.Column('stt_confidence', sa.Float, nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('intent', sa.String(50), nullable=True),
        sa.Column('urgency_score', sa.Integer, nullable=True),
        sa.Column('escalated_to', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Add vector column for conversations (pgvector)
    op.execute('''
        ALTER TABLE conversations 
        ADD COLUMN transcript_embedding vector(1536)
    ''')
    
    # ─────────────── MESSAGES ───────────────
    op.create_table(
        'messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),  # user, assistant, system
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('is_voice', sa.Boolean, default=False),
        sa.Column('audio_ref', sa.String(500), nullable=True),
        sa.Column('agent_type', sa.String(50), nullable=True),  # supervisor, info, action
        sa.Column('tool_calls', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # ─────────────── BOOKINGS ───────────────
    op.create_table(
        'bookings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id'), nullable=True),
        sa.Column('booking_type', sa.String(20), default='flight'),  # flight, hotel, activity
        sa.Column('status', sa.String(20), default='pending'),  # pending, confirmed, cancelled, refunded, failed
        sa.Column('external_id', sa.String(100), nullable=True),
        sa.Column('pnr', sa.String(10), nullable=True),
        sa.Column('details', sa.JSON, nullable=True),
        sa.Column('currency', sa.String(3), default='EUR'),
        sa.Column('total_amount', sa.Float, nullable=True),
        sa.Column('refund_amount', sa.Float, nullable=True),
        sa.Column('travel_date', sa.DateTime, nullable=True),
        sa.Column('booked_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('cancelled_at', sa.DateTime, nullable=True),
    )
    
    # ─────────────── POLICIES ───────────────
    op.create_table(
        'policies',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('category', sa.String(50), nullable=False),  # cancellation, refund, baggage, check-in, general
        sa.Column('provider', sa.String(100), nullable=True),  # airline/hotel name or 'general'
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('effective_date', sa.DateTime, nullable=True),
        sa.Column('expiry_date', sa.DateTime, nullable=True),
        sa.Column('source_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Add vector column for policies (pgvector)
    op.execute('''
        ALTER TABLE policies 
        ADD COLUMN content_embedding vector(1536)
    ''')
    
    # ─────────────── INDEXES ───────────────
    op.create_index('ix_conversations_user', 'conversations', ['user_id'])
    op.create_index('ix_conversations_status', 'conversations', ['status'])
    op.create_index('ix_messages_conversation', 'messages', ['conversation_id'])
    op.create_index('ix_bookings_user', 'bookings', ['user_id'])
    op.create_index('ix_bookings_status', 'bookings', ['status'])
    op.create_index('ix_policies_category', 'policies', ['category'])
    op.create_index('ix_policies_provider', 'policies', ['provider'])
    
    # Vector indexes for similarity search (HNSW - faster for queries)
    op.execute('''
        CREATE INDEX ix_conversations_embedding 
        ON conversations 
        USING hnsw (transcript_embedding vector_cosine_ops)
    ''')
    
    op.execute('''
        CREATE INDEX ix_policies_embedding 
        ON policies 
        USING hnsw (content_embedding vector_cosine_ops)
    ''')


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_policies_embedding', 'policies')
    op.drop_index('ix_conversations_embedding', 'conversations')
    op.drop_index('ix_policies_provider', 'policies')
    op.drop_index('ix_policies_category', 'policies')
    op.drop_index('ix_bookings_status', 'bookings')
    op.drop_index('ix_bookings_user', 'bookings')
    op.drop_index('ix_messages_conversation', 'messages')
    op.drop_index('ix_conversations_status', 'conversations')
    op.drop_index('ix_conversations_user', 'conversations')
    
    # Drop tables (reverse order due to foreign keys)
    op.drop_table('policies')
    op.drop_table('bookings')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('users')
    
    # Drop extension
    op.execute('DROP EXTENSION IF EXISTS vector')