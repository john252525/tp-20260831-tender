import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, String, Text, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin

class Decision(Base, UUIDMixin):
    __tablename__ = 'decisions'

    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenders.id'), nullable=False, unique=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    chosen_supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('suppliers.id'), nullable=True)
    chosen_offer_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('commercial_offers.id'), nullable=True)
    margin_at_decision: Mapped[Optional[float]] = mapped_column(Numeric(18,2), nullable=True)
    risk_level_at_decision: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default='')
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
