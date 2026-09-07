from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '006_add_communications'
down_revision = '005_add_suppliers'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'communications',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('lot_supplier_id', UUID(), nullable=False),
        sa.Column('tender_id', UUID(), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('subject', sa.Text(), nullable=False, server_default=''),
        sa.Column('body_text', sa.Text(), nullable=False, server_default=''),
        sa.Column('body_html', sa.Text(), nullable=False, server_default=''),
        sa.Column('message_type', sa.String(30), nullable=False, server_default='other'),
        sa.Column('external_id', sa.String(500), nullable=False, server_default=''),
        sa.Column('in_reply_to_external_id', sa.String(500), nullable=False, server_default=''),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['lot_supplier_id'], ['lot_suppliers.id'], ),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ),
    )
    op.create_index('idx_comms_lot_supplier', 'communications', ['lot_supplier_id'])
    op.create_index('idx_comms_tender', 'communications', ['tender_id'])
    op.create_index('idx_comms_message_type', 'communications', ['message_type'])
    op.create_index('idx_comms_sent_at', 'communications', ['sent_at'])

    op.create_table(
        'communication_attachments',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('communication_id', UUID(), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=False, server_default='application/octet-stream'),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('is_parsed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['communication_id'], ['communications.id'], ),
    )
    op.create_index('idx_ca_communication', 'communication_attachments', ['communication_id'])

    op.create_table(
        'commercial_offers',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('lot_supplier_id', UUID(), nullable=False),
        sa.Column('tender_id', UUID(), nullable=False),
        sa.Column('source_communication_id', UUID(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='PROCESSING'),
        sa.Column('coverage', sa.Float(), nullable=False, server_default='0'),
        sa.Column('clarification_needed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('clarification_items', JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('total_cost', sa.Numeric(18,2), nullable=True),
        sa.Column('delivery_cost', sa.Numeric(18,2), nullable=True),
        sa.Column('total_cost_with_delivery', sa.Numeric(18,2), nullable=True),
        sa.Column('total_cost_with_all', sa.Numeric(18,2), nullable=True),
        sa.Column('margin_absolute', sa.Numeric(18,2), nullable=True),
        sa.Column('margin_percent', sa.Float(), nullable=True),
        sa.Column('payment_terms', JSONB(), nullable=True),
        sa.Column('delivery_terms', JSONB(), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('raw_text_snippet', sa.Text(), nullable=False, server_default=''),
        sa.Column('parsed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['lot_supplier_id'], ['lot_suppliers.id'], ),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ),
        sa.ForeignKeyConstraint(['source_communication_id'], ['communications.id'], ),
    )
    op.create_index('idx_co_lot_supplier', 'commercial_offers', ['lot_supplier_id'])
    op.create_index('idx_co_tender', 'commercial_offers', ['tender_id'])
    op.create_index('idx_co_status', 'commercial_offers', ['status'])

    op.create_table(
        'offer_positions',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('commercial_offer_id', UUID(), nullable=False),
        sa.Column('tender_position_id', UUID(), nullable=True),
        sa.Column('supplier_name', sa.Text(), nullable=False),
        sa.Column('match_type', sa.String(10), nullable=False, server_default='not_found'),
        sa.Column('match_confidence', sa.Float(), nullable=True),
        sa.Column('price_per_unit', sa.Numeric(18,4), nullable=True),
        sa.Column('quantity_available', sa.Numeric(18,4), nullable=True),
        sa.Column('delivery_days', sa.Integer(), nullable=True),
        sa.Column('nds_included', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('nds_rate', sa.Float(), nullable=True),
        sa.Column('total_price', sa.Numeric(18,2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=False, server_default=''),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['commercial_offer_id'], ['commercial_offers.id'], ),
        sa.ForeignKeyConstraint(['tender_position_id'], ['tender_positions.id'], ),
    )
    op.create_index('idx_op_offer_id', 'offer_positions', ['commercial_offer_id'])
    op.create_index('idx_op_tender_pos', 'offer_positions', ['tender_position_id'])

def downgrade() -> None:
    op.drop_table('offer_positions')
    op.drop_table('commercial_offers')
    op.drop_table('communication_attachments')
    op.drop_table('communications')
