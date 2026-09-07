import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.models.base import Base, UUIDMixin, TimestampMixin

class Category(Base, UUIDMixin, TimestampMixin):
    __tablename__ = 'categories'
    __table_args__ = (
        Index('idx_categories_parent_id', 'parent_id'),
        Index('idx_categories_is_active', 'is_active'),
        # IVFFlat index для ускорения векторного поиска
        Index('idx_categories_embedding', 'embedding', postgresql_using='ivfflat'),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('categories.id'), nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(768), nullable=True)
    embedding_status: Mapped[str] = mapped_column(String(20), nullable=False, default='generating')
    embedding_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
