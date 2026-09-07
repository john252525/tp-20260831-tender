from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '007_add_decisions'
down_revision = '006_add_communications'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'decisions',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tender_id', UUID(), nullable=False),
        sa.Column('decision', sa.String(20), nullable=False),
        sa.Column('chosen_supplier_id', UUID(), nullable=True),
        sa.Column('chosen_offer_id', UUID(), nullable=True),
        sa.Column('margin_at_decision', sa.Numeric(18,2), nullable=True),
        sa.Column('risk_level_at_decision', sa.String(10), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False, server_default=''),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tender_id', name='idx_decisions_tender'),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ),
        sa.ForeignKeyConstraint(['chosen_supplier_id'], ['suppliers.id'], ),
        sa.ForeignKeyConstraint(['chosen_offer_id'], ['commercial_offers.id'], ),
    )

def downgrade() -> None:
    op.drop_table('decisions')
