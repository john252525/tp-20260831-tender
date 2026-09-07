from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class CategoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    keywords: List[str] = Field(default_factory=list)
    parent_id: Optional[UUID] = None

class CategoryUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    keywords: List[str] = Field(default_factory=list)
    parent_id: Optional[UUID] = None

class CategoryPatchRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    keywords: Optional[List[str]] = None
    parent_id: Optional[UUID] = None
    is_active: Optional[bool] = None

class BulkImportRequest(BaseModel):
    categories: List[CategoryCreateRequest] = Field(..., min_length=1, max_length=500)
