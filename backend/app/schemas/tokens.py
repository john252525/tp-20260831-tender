from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ApiTokenCreateRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    rate_limit_per_minute: int = Field(60, ge=1, le=1000)
    expires_in_days: Optional[int] = Field(None, ge=1)

class ApiTokenUpdateRequest(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    is_active: Optional[bool] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=1000)

class ApiTokenListItem(BaseModel):
    id: str
    description: str
    token_preview: str
    is_active: bool
    rate_limit_per_minute: int
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class ApiTokenCreated(BaseModel):
    id: str
    token: str
    description: str
    created_at: datetime
