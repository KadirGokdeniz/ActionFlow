"""add password_hash to users

Revision ID: 002_add_password_hash
Revises: 001_initial
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_password_hash"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(255), nullable=True)
    )

def downgrade():
    op.drop_column("users", "password_hash")
