from alembic import op

revision = '008_change_embedding_dimension'
down_revision = '007_add_decisions'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Меняем размерность векторов с 1536 на 768
    op.execute('ALTER TABLE categories ALTER COLUMN embedding TYPE vector(768);')
    op.execute('ALTER TABLE tenders ALTER COLUMN embedding TYPE vector(768);')

def downgrade() -> None:
    op.execute('ALTER TABLE categories ALTER COLUMN embedding TYPE vector(1536);')
    op.execute('ALTER TABLE tenders ALTER COLUMN embedding TYPE vector(1536);')
