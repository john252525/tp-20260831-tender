"""add_outgoing_drafts

Revision ID: 009_add_outgoing_drafts
Revises: 008_change_embedding_dimension
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '009_add_outgoing_drafts'
down_revision = '008_change_embedding_dimension'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'outgoing_drafts',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tender_id', UUID(), nullable=False),
        sa.Column('supplier_website', sa.Text(), nullable=False, server_default=''),
        sa.Column('supplier_name', sa.String(500), nullable=False, server_default=''),
        sa.Column('email', sa.String(255), nullable=False, server_default=''),
        sa.Column('subject', sa.Text(), nullable=False, server_default=''),
        sa.Column('body_text', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('metadata', JSONB(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_external_id', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_od_tender_id', 'outgoing_drafts', ['tender_id'])
    op.create_index('idx_od_status', 'outgoing_drafts', ['status'])
    op.create_index('idx_od_email', 'outgoing_drafts', ['email'])

def downgrade() -> None:
    op.drop_index('idx_od_email', table_name='outgoing_drafts')
    op.drop_index('idx_od_status', table_name='outgoing_drafts')
    op.drop_index('idx_od_tender_id', table_name='outgoing_drafts')
    op.drop_table('outgoing_drafts')
