from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

class ContactPerson(BaseModel):
    name: str = ''
    position: str = ''
    email: str = ''
    phone: str = ''

class SupplierCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    type: str = Field('unknown', pattern='^(manufacturer|distributor|wholesaler|retail|unknown)$')
    website: str = ''
    email: Optional[EmailStr] = None
    phone: str = ''
    telegram: str = ''
    whatsapp: str = ''
    inn: str = ''
    kpp: str = ''
    ogrn: str = ''
    legal_address: str = ''
    contact_persons: List[ContactPerson] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    notes: str = ''

class SupplierUpdateRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = Field(None, pattern='^(manufacturer|distributor|wholesaler|retail|unknown)$')
    website: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    telegram: Optional[str] = None
    whatsapp: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    ogrn: Optional[str] = None
    legal_address: Optional[str] = None
    contact_persons: Optional[List[ContactPerson]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class SupplierListItem(BaseModel):
    id: UUID
    name: str
    type: str
    website: str
    email: str
    phone: str
    telegram: str
    inn: str
    tags: List[str]
    rating: Dict[str, Any]
    total_lots: int
    successful_deals: int
    total_volume_rub: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

class SupplierDetail(BaseModel):
    id: UUID
    name: str
    type: str
    website: str
    contacts: Dict[str, Any]
    legal_info: Dict[str, str]
    tags: List[str]
    notes: str
    rating: Dict[str, Any]
    statistics: Dict[str, Any]
    recent_tenders: List[Dict[str, Any]]
    is_active: bool
    deleted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
