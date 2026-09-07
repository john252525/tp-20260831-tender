import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.models.base import Base, UUIDMixin, TimestampMixin

class Tender(Base, UUIDMixin, TimestampMixin):
    __tablename__ = 'tenders'
    __table_args__ = (
        Index('idx_tenders_source_id', 'source_id', 'source_tender_id', unique=True),
        Index('idx_tenders_status', 'status'),
        Index('idx_tenders_deadline', 'deadline_at'),
        Index('idx_tenders_nmck', 'nmck'),
        Index('idx_tenders_published', 'published_at'),
        Index('idx_tenders_matched_category', 'matched_category_id'),
        Index('idx_tenders_score', 'score'),
        Index('idx_tenders_created', 'created_at'),
        Index('idx_tenders_embedding', 'embedding', postgresql_using='ivfflat'),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tender_sources.id'), nullable=False)
    source_tender_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default='')
    nmck: Mapped[Optional[float]] = mapped_column(Numeric(18,2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default='RUB')
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    customer_name: Mapped[str] = mapped_column(Text, nullable=False, default='')
    customer_inn: Mapped[str] = mapped_column(String(12), nullable=False, default='')
    customer_kpp: Mapped[str] = mapped_column(String(9), nullable=False, default='')
    platform: Mapped[str] = mapped_column(String(100), nullable=False, default='')
    source_url: Mapped[str] = mapped_column(Text, nullable=False, default='')
    status: Mapped[str] = mapped_column(String(50), nullable=False, default='NEW')
    embedding: Mapped[Optional[list]] = mapped_column(Vector(768), nullable=True)
    structured_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    search_queries: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    matched_category_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('categories.id'), nullable=True)
    similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_components: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    selected_supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)  # без FK, связь с suppliers позже
    final_margin_absolute: Mapped[Optional[float]] = mapped_column(Numeric(18,2), nullable=True)
    final_margin_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    risk_details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
