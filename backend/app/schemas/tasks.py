from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class TaskStatus(BaseModel):
    id: UUID
    celery_task_id: Optional[str]
    task_type: str
    status: str
    progress_percent: float
    entity_type: Optional[str]
    entity_id: Optional[UUID]
    result_summary: Optional[str]
    error_message: Optional[str]
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
