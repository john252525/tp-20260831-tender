import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.tender import Tender
from app.models.lot_supplier import LotSupplier
from app.models.supplier import Supplier
from app.models.communication import Communication
from app.models.task import Task
from app.schemas.communications import SendMessageRequest, RequestCpRequest
from app.workers.tasks import send_communications_task

router = APIRouter()

@router.post('/{tender_id}/request-cp', status_code=status.HTTP_202_ACCEPTED)
async def request_cp(
    tender_id: uuid.UUID,
    payload: RequestCpRequest = Body(default_factory=RequestCpRequest),
    db: AsyncSession = Depends(get_db)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    task = Task(
        task_type='SEND_COMMUNICATIONS',
        status='PENDING',
        entity_type='tender',
        entity_id=tender_id,
        progress_percent=0.0,
        input_data={
            'tender_id': str(tender_id),
            'template_override': payload.template_override.model_dump() if payload.template_override else None,
            'attach_positions_table': payload.attach_positions_table,
            'supplier_ids': [str(sid) for sid in payload.supplier_ids] if payload.supplier_ids else None,
        }
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Проверяем наличие привязанных поставщиков
    lot_query = select(LotSupplier).where(LotSupplier.tender_id == tender_id)
    if payload.supplier_ids:
        lot_query = lot_query.where(LotSupplier.supplier_id.in_(payload.supplier_ids))
    lots = (await db.execute(lot_query)).scalars().all()

    if not lots:
        # Нет поставщиков – сразу завершаем задачу, Celery не вызываем
        task.status = 'COMPLETED'
        task.progress_percent = 100.0
        task.result_summary = 'Нет привязанных поставщиков'
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return {
            'success': True,
            'data': {
                'task_id': str(task.id),
                'status': 'ACCEPTED',
                'estimated_time_seconds': 1,
                'check_url': f'/api/v1/tasks/{task.id}'
            }
        }

    celery_result = send_communications_task.delay(str(task.id))
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

@router.get('/{tender_id}/communications')
async def list_communications(
    tender_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    lots = (await db.execute(
        select(LotSupplier).where(LotSupplier.tender_id == tender_id)
    )).scalars().all()

    threads = []
    for lot in lots:
        supplier = await db.get(Supplier, lot.supplier_id)
        if not supplier:
            continue
        comms = (await db.execute(
            select(Communication).where(Communication.lot_supplier_id == lot.id)
        )).scalars().all()
        messages = []
        for c in comms:
            messages.append({
                'id': str(c.id),
                'direction': c.direction,
                'channel': c.channel,
                'subject': c.subject,
                'body_text': c.body_text,
                'message_type': c.message_type,
                'sent_at': c.sent_at.isoformat() if c.sent_at else None,
                'received_at': c.received_at.isoformat() if c.received_at else None,
            })
        threads.append({
            'lot_supplier_id': str(lot.id),
            'supplier_id': str(supplier.id),
            'supplier_name': supplier.name,
            'status': lot.status,
            'messages': messages,
        })
    return {'success': True, 'data': {'tender_id': str(tender_id), 'supplier_threads': threads}}

@router.post('/{tender_id}/communications/send', status_code=status.HTTP_201_CREATED)
async def send_message(
    tender_id: uuid.UUID,
    payload: SendMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    lot_result = await db.execute(
        select(LotSupplier).where(
            LotSupplier.tender_id == tender_id,
            LotSupplier.supplier_id == payload.supplier_id
        )
    )
    lot = lot_result.scalar_one_or_none()
    if not lot:
        raise NotFoundError('Привязка поставщика к тендеру не найдена')

    comm = Communication(
        lot_supplier_id=lot.id,
        tender_id=tender_id,
        direction='outgoing',
        channel=payload.channel,
        subject=payload.subject,
        body_text=payload.body,
        message_type=payload.message_type,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(comm)
    await db.commit()
    await db.refresh(comm)

    return {
        'success': True,
        'data': {
            'id': str(comm.id),
            'lot_supplier_id': str(comm.lot_supplier_id),
            'tender_id': str(comm.tender_id),
            'direction': comm.direction,
            'channel': comm.channel,
            'subject': comm.subject,
            'body_text': comm.body_text,
            'message_type': comm.message_type,
            'attachments': [],
            'sent_at': comm.sent_at.isoformat() if comm.sent_at else None,
            'received_at': comm.received_at.isoformat() if comm.received_at else None,
        }
    }
