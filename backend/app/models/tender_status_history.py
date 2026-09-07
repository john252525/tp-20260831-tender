import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin

class TenderStatusHistory(Base, UUIDMixin):
    __tablename__ = 'tender_status_history'
    __table_args__ = (
        Index('idx_tsh_tender_id', 'tender_id'),
        Index('idx_tsh_set_at', 'set_at'),
    )

    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenders.id'), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default='')
    set_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
