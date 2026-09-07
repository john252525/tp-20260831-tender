from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.task import Task

router = APIRouter()

@router.get('/{task_id}')
async def get_task_status(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    task = await db.get(Task, task_id)
    if not task:
        raise NotFoundError('Задача не найдена')
    return {
        'success': True,
        'data': _serialize_task(task)
    }

@router.get('')
async def list_tasks(
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(Task)
    count_query = select(func.count(Task.id))

    conditions = []
    if status:
        # Поддержка списка статусов через запятую
        statuses = [s.strip() for s in status.split(',') if s.strip()]
        conditions.append(Task.status.in_(statuses))
    if task_type:
        conditions.append(Task.task_type == task_type)
    if entity_type:
        conditions.append(Task.entity_type == entity_type)
    if entity_id:
        conditions.append(Task.entity_id == entity_id)

    for cond in conditions:
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(Task.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    tasks = result.scalars().all()

    items = [_serialize_task(t) for t in tasks]
    pages = (total + per_page - 1) // per_page
    return {
        'success': True,
        'data': items,
        'meta': {'page': page, 'per_page': per_page, 'total': total, 'pages': pages}
    }

def _serialize_task(task: Task) -> dict:
    return {
        'id': str(task.id),
        'celery_task_id': task.celery_task_id,
        'task_type': task.task_type,
        'status': task.status,
        'progress_percent': task.progress_percent,
        'entity_type': task.entity_type,
        'entity_id': str(task.entity_id) if task.entity_id else None,
        'result_summary': task.result_summary,
        'error_message': task.error_message,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None
    }
