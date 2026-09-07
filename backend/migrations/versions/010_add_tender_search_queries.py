"""add tender search_queries column

Revision ID: 010_add_tender_search_queries
Revises: 009_add_outgoing_drafts
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '010_add_tender_search_queries'
down_revision = '009_add_outgoing_drafts'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('tenders', sa.Column('search_queries', JSONB(), nullable=True))

def downgrade() -> None:
    op.drop_column('tenders', 'search_queries')
