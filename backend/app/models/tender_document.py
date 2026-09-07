import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Index, BigInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin

class TenderDocument(Base, UUIDMixin):
    __tablename__ = 'tender_documents'
    __table_args__ = (
        Index('idx_td_tender_id', 'tender_id'),
    )

    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenders.id'), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default='application/octet-stream')
    source_url: Mapped[str] = mapped_column(Text, nullable=False, default='')
    storage_path: Mapped[str] = mapped_column(Text, nullable=False, default='')
    parsed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(String(20), nullable=False, default='PENDING')
    parse_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
