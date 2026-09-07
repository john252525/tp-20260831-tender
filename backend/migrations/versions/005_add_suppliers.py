from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '005_add_suppliers'
down_revision = '004_add_tenders'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'suppliers',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('type', sa.String(20), nullable=False, server_default='unknown'),
        sa.Column('website', sa.Text(), nullable=False, server_default=''),
        sa.Column('email', sa.String(255), nullable=False, server_default=''),
        sa.Column('phone', sa.String(50), nullable=False, server_default=''),
        sa.Column('telegram', sa.String(100), nullable=False, server_default=''),
        sa.Column('whatsapp', sa.String(50), nullable=False, server_default=''),
        sa.Column('contact_persons', JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('inn', sa.String(12), nullable=False, server_default=''),
        sa.Column('kpp', sa.String(9), nullable=False, server_default=''),
        sa.Column('ogrn', sa.String(15), nullable=False, server_default=''),
        sa.Column('legal_address', sa.Text(), nullable=False, server_default=''),
        sa.Column('tags', JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('rating', JSONB(), nullable=False, server_default=sa.text("'{\"avg_response_time_hours\": null, \"response_rate\": 0, \"price_competitiveness\": 0, \"reliability\": 0}'::jsonb")),
        sa.Column('total_lots', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_deals', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_volume_rub', sa.Numeric(18,2), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_suppliers_email', 'suppliers', ['email'], postgresql_where="email != ''")
    op.create_index('idx_suppliers_inn', 'suppliers', ['inn'], postgresql_where="inn != ''")
    op.create_index('idx_suppliers_type', 'suppliers', ['type'])
    op.create_index('idx_suppliers_tags', 'suppliers', ['tags'], postgresql_using='gin')
    op.create_index('idx_suppliers_deleted_at', 'suppliers', ['deleted_at'])

    op.create_table(
        'lot_suppliers',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tender_id', UUID(), nullable=False),
        sa.Column('supplier_id', UUID(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source', sa.String(20), nullable=False, server_default='manual'),
        sa.Column('match_relevance', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ls_tender_supplier', 'lot_suppliers', ['tender_id', 'supplier_id'], unique=True)
    op.create_index('idx_ls_tender_id', 'lot_suppliers', ['tender_id'])
    op.create_index('idx_ls_supplier_id', 'lot_suppliers', ['supplier_id'])
    op.create_index('idx_ls_status', 'lot_suppliers', ['status'])

def downgrade() -> None:
    op.drop_table('lot_suppliers')
    op.drop_table('suppliers')
