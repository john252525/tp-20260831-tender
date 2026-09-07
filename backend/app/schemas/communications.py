from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

class TemplateOverride(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None

class RequestCpRequest(BaseModel):
    template_override: Optional[TemplateOverride] = None
    attach_positions_table: bool = True
    supplier_ids: Optional[List[UUID]] = None

class SendMessageRequest(BaseModel):
    supplier_id: UUID = Field(...)
    channel: str = Field(..., pattern='^(email|telegram|whatsapp)$')
    subject: str = ''
    body: str = ''
    message_type: str = Field('manual', pattern='^(cp_request|clarification|negotiation|reminder|manual|other)$')
    attachments_file_ids: List[UUID] = Field(default_factory=list)

class CommunicationResponse(BaseModel):
    id: UUID
    lot_supplier_id: UUID
    tender_id: UUID
    direction: str
    channel: str
    subject: str
    body_text: str
    message_type: str
    attachments: List[Dict[str, Any]] = []
    sent_at: Optional[datetime]
    received_at: Optional[datetime]
