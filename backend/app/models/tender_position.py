import uuid
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, Index, Numeric, Text, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin

class TenderPosition(Base, UUIDMixin):
    __tablename__ = 'tender_positions'
    __table_args__ = (
        Index('idx_tp_tender_id', 'tender_id'),
    )

    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenders.id'), nullable=False)
    position_number: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    characteristics: Mapped[str] = mapped_column(Text, nullable=False, default='')
    gost: Mapped[str] = mapped_column(String(100), nullable=False, default='')
    okpd2: Mapped[str] = mapped_column(String(20), nullable=False, default='')
    quantity: Mapped[float] = mapped_column(Numeric(18,4), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default='шт')
    is_essential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default='')
