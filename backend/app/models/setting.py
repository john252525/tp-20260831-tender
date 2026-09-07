import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin

class Setting(Base, UUIDMixin):
    __tablename__ = 'settings'
    __table_args__ = (
        UniqueConstraint('section', 'key', name='idx_settings_section_key'),
    )

    section: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    description: Mapped[str] = mapped_column(Text, nullable=False, default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class SettingHistory(Base, UUIDMixin):
    __tablename__ = 'settings_history'
    __table_args__ = (
        Index('idx_settings_history_section_key', 'section', 'key'),
        Index('idx_settings_history_changed_at', 'changed_at'),
    )

    setting_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('settings.id', ondelete='SET NULL'),
        nullable=True
    )
    section: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
