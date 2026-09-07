import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.tender_source import TenderSource
from app.models.task import Task
from app.schemas.tender_sources import TenderSourceCreateRequest, TenderSourceUpdateRequest
from app.services.encryption_service import encryption_service
from app.workers.tasks import sync_tenders_task
from app.services.gosplan_client import GosPlanClient
import time
from datetime import datetime, timezone

router = APIRouter()

@router.get('')
async def list_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TenderSource).order_by(TenderSource.created_at.desc()))
    sources = result.scalars().all()
    return {
        'success': True,
        'data': [
            {
                'id': str(s.id),
                'name': s.name,
                'type': s.type,
                'api_url': s.api_url,
                'is_active': s.is_active,
                'last_sync_at': s.last_sync_at.isoformat() if s.last_sync_at else None,
                'last_sync_status': s.last_sync_status,
                'last_error': s.last_error,
                'tenders_synced_total': 0,
                'config': s.config or {},
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'updated_at': s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sources
        ],
        'meta': {'page': 1, 'per_page': len(sources), 'total': len(sources), 'pages': 1 if sources else 0}
    }


@router.post('', status_code=status.HTTP_201_CREATED)
async def create_source(payload: TenderSourceCreateRequest, db: AsyncSession = Depends(get_db)):
    source = TenderSource(
        name=payload.name,
        type=payload.type,
        api_url=payload.api_url,
        api_key_encrypted=encryption_service.encrypt(payload.api_key),
        config=payload.config or {},
        is_active=True,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    return {
        'success': True,
        'data': {
            'id': str(source.id),
            'name': source.name,
            'type': source.type,
            'api_url': source.api_url,
            'is_active': source.is_active,
            'last_sync_at': source.last_sync_at.isoformat() if source.last_sync_at else None,
            'last_sync_status': source.last_sync_status,
            'last_error': source.last_error,
            'config': source.config,
            'created_at': source.created_at.isoformat() if source.created_at else None,
            'updated_at': source.updated_at.isoformat() if source.updated_at else None,
        }
    }


@router.get('/{source_id}')
async def get_source(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    source = await db.get(TenderSource, source_id)
    if not source:
        raise NotFoundError('Источник не найден')

    return {
        'success': True,
        'data': {
            'id': str(source.id),
            'name': source.name,
            'type': source.type,
            'api_url': source.api_url,
            'is_active': source.is_active,
            'last_sync_at': source.last_sync_at.isoformat() if source.last_sync_at else None,
            'last_sync_status': source.last_sync_status,
            'last_error': source.last_error,
            'config': source.config,
            'created_at': source.created_at.isoformat() if source.created_at else None,
            'updated_at': source.updated_at.isoformat() if source.updated_at else None,
        }
    }


@router.put('/{source_id}')
async def update_source(source_id: uuid.UUID, payload: TenderSourceUpdateRequest, db: AsyncSession = Depends(get_db)):
    source = await db.get(TenderSource, source_id)
    if not source:
        raise NotFoundError('Источник не найден')

    data = payload.model_dump(exclude_unset=True)
    if 'api_key' in data and data['api_key'] is not None:
        source.api_key_encrypted = encryption_service.encrypt(data.pop('api_key'))
    for field, value in data.items():
        setattr(source, field, value)

    await db.commit()
    await db.refresh(source)
    return {
        'success': True,
        'data': {
            'id': str(source.id),
            'name': source.name,
            'type': source.type,
            'api_url': source.api_url,
            'is_active': source.is_active,
            'last_sync_at': source.last_sync_at.isoformat() if source.last_sync_at else None,
            'last_sync_status': source.last_sync_status,
            'last_error': source.last_error,
            'config': source.config,
            'created_at': source.created_at.isoformat() if source.created_at else None,
            'updated_at': source.updated_at.isoformat() if source.updated_at else None,
        }
    }


@router.patch('/{source_id}')
async def patch_source(source_id: uuid.UUID, payload: TenderSourceUpdateRequest, db: AsyncSession = Depends(get_db)):
    source = await db.get(TenderSource, source_id)
    if not source:
        raise NotFoundError('Источник не найден')

    data = payload.model_dump(exclude_unset=True)
    if 'api_key' in data and data.get('api_key') is not None:
        source.api_key_encrypted = encryption_service.encrypt(data.pop('api_key'))
    for field, value in data.items():
        setattr(source, field, value)

    await db.commit()
    await db.refresh(source)
    return {
        'success': True,
        'data': {
            'id': str(source.id),
            'name': source.name,
            'type': source.type,
            'api_url': source.api_url,
            'is_active': source.is_active,
            'last_sync_at': source.last_sync_at.isoformat() if source.last_sync_at else None,
            'last_sync_status': source.last_sync_status,
            'last_error': source.last_error,
            'config': source.config,
            'created_at': source.created_at.isoformat() if source.created_at else None,
            'updated_at': source.updated_at.isoformat() if source.updated_at else None,
        }
    }


@router.delete('/{source_id}')
async def delete_source(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    source = await db.get(TenderSource, source_id)
    if not source:
        raise NotFoundError('Источник не найден')
    source.is_active = False
    await db.commit()
    return {'success': True, 'data': {'id': str(source.id), 'is_active': source.is_active}}


@router.post('/{source_id}/test-connection')
async def test_connection(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    source = await db.get(TenderSource, source_id)
    if not source:
        raise NotFoundError('Источник не найден')

    if 'gosplan.info' not in (source.api_url or ''):
        return {
            'success': True,
            'data': {
                'reachable': False,
                'latency_ms': None,
                'tenders_available': None,
                'error': 'Проверка подключения поддерживается только для источников ГосПлан'
            }
        }

    try:
        start = time.monotonic()
        client = GosPlanClient(base_url=source.api_url)
        purchases = await client.search_purchases(limit=1, skip=0)
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            'success': True,
            'data': {
                'reachable': True,
                'latency_ms': latency_ms,
                'tenders_available': len(purchases),
                'error': None
            }
        }
    except Exception as exc:
        return {
            'success': True,
            'data': {
                'reachable': False,
                'latency_ms': None,
                'tenders_available': None,
                'error': str(exc)
            }
        }



@router.post('/{source_id}/sync', status_code=status.HTTP_202_ACCEPTED)
async def sync_source(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    source = await db.get(TenderSource, source_id)
    if not source:
        raise NotFoundError('Источник не найден')

    task = Task(
        task_type='SYNC_TENDERS',
        status='PENDING',
        entity_type='tender_source',
        entity_id=source.id,
        progress_percent=0.0,
        input_data={'source_id': str(source_id)}
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Ставим Celery-задачу
    celery_result = sync_tenders_task.delay(str(task.id))
    task.celery_task_id = celery_result.id
    await db.commit()

    return {
        'success': True,
        'data': {
            'task_id': str(task.id),
            'status': 'ACCEPTED',
            'estimated_time_seconds': 120,
            'check_url': f'/api/v1/tasks/{task.id}'
        }
    }
