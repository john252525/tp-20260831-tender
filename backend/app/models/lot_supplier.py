import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin, TimestampMixin

class LotSupplier(Base, UUIDMixin, TimestampMixin):
    __tablename__ = 'lot_suppliers'
    __table_args__ = (
        Index('idx_ls_tender_supplier', 'tender_id', 'supplier_id', unique=True),
        Index('idx_ls_tender_id', 'tender_id'),
        Index('idx_ls_supplier_id', 'supplier_id'),
        Index('idx_ls_status', 'status'),
    )

    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenders.id'), nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('suppliers.id'), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default='PENDING')
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default='manual')  # google, internal_db, manual
    match_relevance: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # high, medium, low
