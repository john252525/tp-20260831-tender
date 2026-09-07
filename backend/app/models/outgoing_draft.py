import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin, TimestampMixin

class OutgoingDraft(Base, UUIDMixin, TimestampMixin):
    """Черновик письма поставщику, сформированный автоматически (до отправки)."""

    __tablename__ = 'outgoing_drafts'
    __table_args__ = (
        Index('idx_od_tender_id', 'tender_id'),
        Index('idx_od_status', 'status'),
        Index('idx_od_email', 'email'),
    )

    tender_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    supplier_website: Mapped[str] = mapped_column(Text, nullable=False, default='')
    supplier_name: Mapped[str] = mapped_column(String(500), nullable=False, default='')
    email: Mapped[str] = mapped_column(String(255), nullable=False, default='')
    subject: Mapped[str] = mapped_column(Text, nullable=False, default='')
    body_text: Mapped[str] = mapped_column(Text, nullable=False, default='')
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='draft')  # draft, sent, cancelled
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_external_id: Mapped[str] = mapped_column(Text, nullable=False, default='')
