"""Add travel_context and agent_state to conversations

Revision ID: 002_add_travel_context
Revises: 001_initial
Create Date: 2026-01-20

Adds JSON columns to persist orchestrator state between conversation turns:
- travel_context: Stores collected travel information (destination, dates, etc.)
- agent_state: Stores current conversation state and flags
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_travel_context'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add travel_context and agent_state JSON columns to conversations
    op.add_column('conversations', 
        sa.Column('travel_context', sa.JSON, nullable=True)
    )
    op.add_column('conversations', 
        sa.Column('agent_state', sa.JSON, nullable=True)
    )


def downgrade() -> None:
    # Remove the columns
    op.drop_column('conversations', 'agent_state')
    op.drop_column('conversations', 'travel_context')
