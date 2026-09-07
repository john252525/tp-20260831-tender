import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin

class Supplier(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = 'suppliers'
    __table_args__ = (
        Index('idx_suppliers_email', 'email', postgresql_where="email != ''"),
        Index('idx_suppliers_inn', 'inn', postgresql_where="inn != ''"),
        Index('idx_suppliers_type', 'type'),
        Index('idx_suppliers_tags', 'tags', postgresql_using='gin'),
        Index('idx_suppliers_deleted_at', 'deleted_at'),
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default='unknown')
    website: Mapped[str] = mapped_column(Text, nullable=False, default='')
    email: Mapped[str] = mapped_column(String(255), nullable=False, default='')
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default='')
    telegram: Mapped[str] = mapped_column(String(100), nullable=False, default='')
    whatsapp: Mapped[str] = mapped_column(String(50), nullable=False, default='')
    contact_persons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    inn: Mapped[str] = mapped_column(String(12), nullable=False, default='')
    kpp: Mapped[str] = mapped_column(String(9), nullable=False, default='')
    ogrn: Mapped[str] = mapped_column(String(15), nullable=False, default='')
    legal_address: Mapped[str] = mapped_column(Text, nullable=False, default='')
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default='')
    rating: Mapped[dict] = mapped_column(JSONB, nullable=False, default=lambda: {
        'avg_response_time_hours': None,
        'response_rate': 0,
        'price_competitiveness': 0,
        'reliability': 0,
    })
    total_lots: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_deals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_volume_rub: Mapped[float] = mapped_column(Numeric(18,2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
