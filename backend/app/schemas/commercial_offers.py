from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel

class CommercialOfferListItem(BaseModel):
    id: UUID
    tender_id: UUID
    tender_title: str
    supplier_id: UUID
    supplier_name: str
    status: str
    coverage: float
    total_cost_with_all: Optional[float]
    margin_absolute: Optional[float]
    margin_percent: Optional[float]
    clarification_needed: bool
    received_at: Optional[datetime]

class CommercialOfferDetail(BaseModel):
    id: UUID
    tender_id: UUID
    supplier_id: UUID
    source_communication_id: Optional[UUID]
    status: str
    coverage: float
    clarification_needed: bool
    clarification_items: List[str]
    positions: List[Dict[str, Any]]
    delivery_terms: Optional[Dict[str, Any]]
    payment_terms: Optional[Dict[str, Any]]
    calculated: Optional[Dict[str, Any]]
    valid_until: Optional[datetime]
    raw_text_snippet: str
    received_at: Optional[datetime]
    parsed_at: Optional[datetime]
