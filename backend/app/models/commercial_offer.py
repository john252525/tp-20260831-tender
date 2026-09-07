import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin, TimestampMixin

class CommercialOffer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = 'commercial_offers'
    __table_args__ = (
        Index('idx_co_lot_supplier', 'lot_supplier_id'),
        Index('idx_co_tender', 'tender_id'),
        Index('idx_co_status', 'status'),
    )

    lot_supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('lot_suppliers.id'), nullable=False)
    tender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenders.id'), nullable=False)
    source_communication_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('communications.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='PROCESSING')
    coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    clarification_needed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    clarification_items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    total_cost: Mapped[Optional[float]] = mapped_column(Numeric(18,2), nullable=True)
    delivery_cost: Mapped[Optional[float]] = mapped_column(Numeric(18,2), nullable=True)
    total_cost_with_delivery: Mapped[Optional[float]] = mapped_column(Numeric(18,2), nullable=True)
    total_cost_with_all: Mapped[Optional[float]] = mapped_column(Numeric(18,2), nullable=True)
    margin_absolute: Mapped[Optional[float]] = mapped_column(Numeric(18,2), nullable=True)
    margin_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payment_terms: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    delivery_terms: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_text_snippet: Mapped[str] = mapped_column(Text, nullable=False, default='')
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class OfferPosition(Base, UUIDMixin):
    __tablename__ = 'offer_positions'
    __table_args__ = (
        Index('idx_op_offer_id', 'commercial_offer_id'),
        Index('idx_op_tender_pos', 'tender_position_id'),
    )

    commercial_offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('commercial_offers.id'), nullable=False)
    tender_position_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('tender_positions.id'), nullable=True)
    supplier_name: Mapped[str] = mapped_column(Text, nullable=False)
    match_type: Mapped[str] = mapped_column(String(10), nullable=False, default='not_found')
    match_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_per_unit: Mapped[Optional[float]] = mapped_column(Numeric(18,4), nullable=True)
    quantity_available: Mapped[Optional[float]] = mapped_column(Numeric(18,4), nullable=True)
    delivery_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nds_included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    nds_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_price: Mapped[Optional[float]] = mapped_column(Numeric(18,2), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default='')
