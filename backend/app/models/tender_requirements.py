import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin

class TenderRequirements(Base, UUIDMixin):
    __tablename__ = 'tender_requirements'
    __table_args__ = (
        Index('idx_tr_tender_id', 'tender_id', unique=True),
    )

    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenders.id'), nullable=False)
    delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_address: Mapped[str] = mapped_column(Text, nullable=False, default='')
    delivery_conditions: Mapped[str] = mapped_column(Text, nullable=False, default='')
    license_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sro_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    security_bid: Mapped[Optional[float]] = mapped_column(Numeric(18,2), nullable=True)
    security_contract: Mapped[Optional[float]] = mapped_column(Numeric(18,2), nullable=True)
    prepayment_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stages_count: Mapped[int] = mapped_column(default=1, nullable=False)
    special_conditions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
