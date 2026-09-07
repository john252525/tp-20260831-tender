from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

class TenderSourceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern='^(aggregator_api|direct_api)$')
    api_url: str = Field(..., pattern=r'^https://')
    api_key: str = Field(..., min_length=1)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)

class TenderSourceUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    api_url: Optional[str] = Field(None, pattern=r'^https://')
    api_key: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class TenderSourceListItem(BaseModel):
    id: UUID
    name: str
    type: str
    api_url: str
    is_active: bool
    last_sync_at: Optional[datetime]
    last_sync_status: Optional[str]
    last_error: Optional[str]
    tenders_synced_total: int = 0
    created_at: datetime

class TenderSource(BaseModel):
    id: UUID
    name: str
    type: str
    api_url: str
    config: Dict[str, Any]
    is_active: bool
    last_sync_at: Optional[datetime]
    last_sync_status: Optional[str]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime
