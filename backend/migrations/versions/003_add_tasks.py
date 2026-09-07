from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '003_add_tasks'
down_revision = '002_seed_settings'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'tasks',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', UUID(), nullable=True),
        sa.Column('progress_percent', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('input_data', JSONB(), nullable=True),
        sa.Column('output_data', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_tasks_status', 'tasks', ['status'])
    op.create_index('idx_tasks_entity', 'tasks', ['entity_type', 'entity_id'])

def downgrade() -> None:
    op.drop_index('idx_tasks_entity', table_name='tasks')
    op.drop_index('idx_tasks_status', table_name='tasks')
    op.drop_table('tasks')
