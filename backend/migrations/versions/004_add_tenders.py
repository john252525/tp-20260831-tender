from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector

revision = '004_add_tenders'
down_revision = '003_add_tasks'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'tender_sources',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('api_url', sa.Text(), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=False),
        sa.Column('config', JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_status', sa.String(20), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # Создаём seed-источник для ручного ввода
    bind = op.get_bind()
    bind.execute(sa.text("""
        INSERT INTO tender_sources (id, name, type, api_url, api_key_encrypted, config, is_active, created_at, updated_at)
        VALUES ('00000000-0000-0000-0000-000000000001', 'Ручной ввод', 'direct_api', 'https://manual.local', '', '{}', true, now(), now())
    """))

    op.create_table(
        'tenders',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_id', UUID(), nullable=False),
        sa.Column('source_tender_id', sa.String(255), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('nmck', sa.Numeric(18,2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='RUB'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deadline_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('customer_name', sa.Text(), nullable=False, server_default=''),
        sa.Column('customer_inn', sa.String(12), nullable=False, server_default=''),
        sa.Column('customer_kpp', sa.String(9), nullable=False, server_default=''),
        sa.Column('platform', sa.String(100), nullable=False, server_default=''),
        sa.Column('source_url', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(50), nullable=False, server_default='NEW'),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('structured_data', JSONB(), nullable=True),
        sa.Column('matched_category_id', UUID(), nullable=True),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('score_components', JSONB(), nullable=True),
        sa.Column('selected_supplier_id', UUID(), nullable=True),
        sa.Column('final_margin_absolute', sa.Numeric(18,2), nullable=True),
        sa.Column('final_margin_percent', sa.Float(), nullable=True),
        sa.Column('risk_level', sa.String(10), nullable=True),
        sa.Column('risk_details', JSONB(), nullable=True),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['source_id'], ['tender_sources.id'], ),
        sa.ForeignKeyConstraint(['matched_category_id'], ['categories.id'], ),
    )
    op.create_index('idx_tenders_source_id', 'tenders', ['source_id', 'source_tender_id'], unique=True)
    op.create_index('idx_tenders_status', 'tenders', ['status'])
    op.create_index('idx_tenders_deadline', 'tenders', ['deadline_at'])
    op.create_index('idx_tenders_nmck', 'tenders', ['nmck'])
    op.create_index('idx_tenders_published', 'tenders', ['published_at'])
    op.create_index('idx_tenders_matched_category', 'tenders', ['matched_category_id'])
    op.create_index('idx_tenders_score', 'tenders', ['score'])
    op.create_index('idx_tenders_created', 'tenders', ['created_at'])
    op.execute(
        "CREATE INDEX idx_tenders_embedding ON tenders USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
    )

    op.create_table(
        'tender_documents',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tender_id', UUID(), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=False, server_default='application/octet-stream'),
        sa.Column('source_url', sa.Text(), nullable=False, server_default=''),
        sa.Column('storage_path', sa.Text(), nullable=False, server_default=''),
        sa.Column('parsed_text', sa.Text(), nullable=True),
        sa.Column('parse_status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('parse_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ),
    )
    op.create_index('idx_td_tender_id', 'tender_documents', ['tender_id'])

    op.create_table(
        'tender_positions',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tender_id', UUID(), nullable=False),
        sa.Column('position_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('characteristics', sa.Text(), nullable=False, server_default=''),
        sa.Column('gost', sa.String(100), nullable=False, server_default=''),
        sa.Column('okpd2', sa.String(20), nullable=False, server_default=''),
        sa.Column('quantity', sa.Numeric(18,4), nullable=False),
        sa.Column('unit', sa.String(50), nullable=False, server_default='шт'),
        sa.Column('is_essential', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=False, server_default=''),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ),
    )
    op.create_index('idx_tp_tender_id', 'tender_positions', ['tender_id'])

    op.create_table(
        'tender_requirements',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tender_id', UUID(), nullable=False),
        sa.Column('delivery_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_address', sa.Text(), nullable=False, server_default=''),
        sa.Column('delivery_conditions', sa.Text(), nullable=False, server_default=''),
        sa.Column('license_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sro_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('security_bid', sa.Numeric(18,2), nullable=True),
        sa.Column('security_contract', sa.Numeric(18,2), nullable=True),
        sa.Column('prepayment_percent', sa.Float(), nullable=True),
        sa.Column('stages_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('special_conditions', JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ),
    )
    op.create_index('idx_tr_tender_id', 'tender_requirements', ['tender_id'], unique=True)

    op.create_table(
        'tender_status_history',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tender_id', UUID(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('previous_status', sa.String(50), nullable=True),
        sa.Column('note', sa.Text(), nullable=False, server_default=''),
        sa.Column('set_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ),
    )
    op.create_index('idx_tsh_tender_id', 'tender_status_history', ['tender_id'])
    op.create_index('idx_tsh_set_at', 'tender_status_history', ['set_at'])

def downgrade() -> None:
    op.drop_table('tender_status_history')
    op.drop_table('tender_requirements')
    op.drop_table('tender_positions')
    op.drop_table('tender_documents')
    op.drop_table('tenders')
    op.drop_table('tender_sources')
