from typing import Any, Optional
from pydantic import BaseModel

class SuccessResponse(BaseModel):
    success: bool = True
    data: Any = None
    meta: Optional[dict] = None

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail

class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int

class AsyncTaskResponse(BaseModel):
    success: bool = True
    data: dict
