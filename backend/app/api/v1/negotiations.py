import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.tender import Tender
from app.models.task import Task
from app.workers.tasks import negotiate_task
from app.services.negotiation_service import get_negotiation_status

router = APIRouter()

@router.post('/tenders/{tender_id}/negotiate', status_code=status.HTTP_202_ACCEPTED)
async def start_negotiation(tender_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(get_db)):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    task = Task(
        task_type='NEGOTIATE',
        status='PENDING',
        entity_type='tender',
        entity_id=tender.id,
        progress_percent=0.0,
        input_data={'tender_id': str(tender_id), 'action': payload.get('action')}
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    celery_result = negotiate_task.delay(str(task.id))
    task.celery_task_id = celery_result.id
    await db.commit()

    return {
        'success': True,
        'data': {
            'task_id': str(task.id),
            'status': 'ACCEPTED',
            'estimated_time_seconds': 30,
            'check_url': f'/api/v1/tasks/{task.id}'
        }
    }

@router.get('/tenders/{tender_id}/negotiation-status')
async def negotiation_status(tender_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')
    status_data = await get_negotiation_status(tender_id, db)
    return {'success': True, 'data': status_data}
