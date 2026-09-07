from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.create_table(
        'api_tokens',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('token', sa.String(64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_api_tokens_token', 'api_tokens', ['token'], unique=True)

    op.create_table(
        'settings',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('section', sa.String(50), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', JSONB(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('section', 'key', name='idx_settings_section_key')
    )

    op.create_table(
        'settings_history',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('setting_id', UUID(), nullable=True),
        sa.Column('section', sa.String(50), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('old_value', JSONB(), nullable=True),
        sa.Column('new_value', JSONB(), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['setting_id'], ['settings.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_settings_history_section_key', 'settings_history', ['section', 'key'])
    op.create_index('idx_settings_history_changed_at', 'settings_history', ['changed_at'])

    op.create_table(
        'categories',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('keywords', JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('parent_id', UUID(), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('embedding_status', sa.String(20), nullable=False, server_default='generating'),
        sa.Column('embedding_generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], ),
    )
    op.create_index('idx_categories_parent_id', 'categories', ['parent_id'])
    op.create_index('idx_categories_is_active', 'categories', ['is_active'])
    # Создаём ivfflat индекс через сырой SQL для надёжности
    op.execute(
        "CREATE INDEX idx_categories_embedding ON categories "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
    )

def downgrade() -> None:
    op.drop_table('categories')
    op.drop_table('settings_history')
    op.drop_table('settings')
    op.drop_table('api_tokens')
    op.execute('DROP EXTENSION IF EXISTS vector')
