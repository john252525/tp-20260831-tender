from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.suppliers import SupplierCreateRequest

class TenderCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=1000)
    description: str = ''
    nmck: Optional[float] = Field(None, ge=0)
    published_at: Optional[datetime] = None
    deadline_at: Optional[datetime] = None
    customer_name: str = ''
    customer_inn: str = ''
    customer_kpp: str = ''
    platform: str = ''
    source_url: str = ''
    documents_urls: List[str] = Field(default_factory=list)
    skip_auto_processing: bool = False

class TenderUpdateRequest(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None

class ReprocessRequest(BaseModel):
    from_stage: str = Field(..., pattern='^(DOCUMENTS_LOADING|SEMANTIC_FILTERING|SCORING|SUPPLIER_SEARCH)$')

class SearchSuppliersRequest(BaseModel):
    max_suppliers: int = Field(10, ge=1, le=50)
    channels: List[Literal['google', 'internal_db']] = Field(default_factory=lambda: ['google', 'internal_db'])
    priority_order: List[Literal['manufacturer', 'distributor', 'wholesaler', 'retail', 'unknown']] = Field(
        default_factory=lambda: ['manufacturer', 'distributor', 'wholesaler']
    )

class ConfirmSuppliersRequest(BaseModel):
    supplier_ids: List[UUID] = Field(default_factory=list)
    new_suppliers: List[SupplierCreateRequest] = Field(default_factory=list)


class RunPipelineRequest(BaseModel):
    pass

class SendDraftsRequest(BaseModel):
    draft_ids: List[UUID] = Field(default_factory=list)
