import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin

class Communication(Base, UUIDMixin):
    __tablename__ = 'communications'
    __table_args__ = (
        Index('idx_comms_lot_supplier', 'lot_supplier_id'),
        Index('idx_comms_tender', 'tender_id'),
        Index('idx_comms_message_type', 'message_type'),
        Index('idx_comms_sent_at', 'sent_at'),
    )

    lot_supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('lot_suppliers.id'), nullable=False)
    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenders.id'), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False, default='')
    body_text: Mapped[str] = mapped_column(Text, nullable=False, default='')
    body_html: Mapped[str] = mapped_column(Text, nullable=False, default='')
    message_type: Mapped[str] = mapped_column(String(30), nullable=False, default='other')
    external_id: Mapped[str] = mapped_column(String(500), nullable=False, default='')
    in_reply_to_external_id: Mapped[str] = mapped_column(String(500), nullable=False, default='')
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class CommunicationAttachment(Base, UUIDMixin):
    __tablename__ = 'communication_attachments'
    __table_args__ = (
        Index('idx_ca_communication', 'communication_id'),
    )

    communication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('communications.id'), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default='application/octet-stream')
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    is_parsed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
