import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.tender import Tender
from app.models.tender_source import TenderSource
from app.models.tender_document import TenderDocument
from app.models.tender_position import TenderPosition
from app.models.tender_requirements import TenderRequirements
from app.models.tender_status_history import TenderStatusHistory
from app.models.task import Task
from app.models.category import Category
from app.models.lot_supplier import LotSupplier
from app.models.supplier import Supplier
from app.models.commercial_offer import CommercialOffer
from app.schemas.tenders import TenderCreateRequest, TenderUpdateRequest, ReprocessRequest, SearchSuppliersRequest, ConfirmSuppliersRequest, SendDraftsRequest
from app.services.tender_processor import process_tender
from app.services.supplier_search import search_suppliers_for_tender
from app.workers.tasks import process_tender_task, search_suppliers_task

router = APIRouter()

MANUAL_SOURCE_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')

@router.get('')
async def list_tenders(
    status: Optional[str] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    source_id: Optional[uuid.UUID] = Query(None),
    nmck_min: Optional[float] = Query(None),
    nmck_max: Optional[float] = Query(None),
    published_after: Optional[datetime] = Query(None),
    published_before: Optional[datetime] = Query(None),
    deadline_after: Optional[datetime] = Query(None),
    deadline_before: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    has_score: Optional[bool] = Query(None),
    score_min: Optional[float] = Query(None),
    score_max: Optional[float] = Query(None),
    sort_by: str = Query('updated_at'),
    sort_order: str = Query('desc'),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(Tender)
    count_query = select(func.count(Tender.id))

    conditions = []
    if status:
        conditions.append(Tender.status == status)
    if category_id:
        conditions.append(Tender.matched_category_id == category_id)
    if source_id:
        conditions.append(Tender.source_id == source_id)
    if nmck_min is not None:
        conditions.append(Tender.nmck >= nmck_min)
    if nmck_max is not None:
        conditions.append(Tender.nmck <= nmck_max)
    if published_after:
        conditions.append(Tender.published_at >= published_after)
    if published_before:
        conditions.append(Tender.published_at <= published_before)
    if deadline_after:
        conditions.append(Tender.deadline_at >= deadline_after)
    if deadline_before:
        conditions.append(Tender.deadline_at <= deadline_before)
    if search:
        pattern = f'%{search}%'
        conditions.append(or_(
            Tender.title.ilike(pattern),
            Tender.description.ilike(pattern),
            Tender.customer_name.ilike(pattern),
            Tender.source_tender_id.ilike(pattern)
        ))
    if has_score is not None:
        if has_score:
            conditions.append(Tender.score.is_not(None))
        else:
            conditions.append(Tender.score.is_(None))
    if score_min is not None:
        conditions.append(Tender.score >= score_min)
    if score_max is not None:
        conditions.append(Tender.score <= score_max)

    for cond in conditions:
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = (await db.execute(count_query)).scalar_one()

    sort_column = getattr(Tender, sort_by, Tender.updated_at)
    if sort_order.lower() == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    tenders = result.scalars().all()

    tender_ids = [t.id for t in tenders]
    positions_counts: Dict[uuid.UUID, int] = {}
    documents_counts: Dict[uuid.UUID, int] = {}
    if tender_ids:
        positions_rows = await db.execute(
            select(TenderPosition.tender_id, func.count(TenderPosition.id))
            .where(TenderPosition.tender_id.in_(tender_ids))
            .group_by(TenderPosition.tender_id)
        )
        positions_counts = {row[0]: row[1] for row in positions_rows.all()}
        documents_rows = await db.execute(
            select(TenderDocument.tender_id, func.count(TenderDocument.id))
            .where(TenderDocument.tender_id.in_(tender_ids))
            .group_by(TenderDocument.tender_id)
        )
        documents_counts = {row[0]: row[1] for row in documents_rows.all()}

    items = []
    for t in tenders:
        items.append({
            'id': str(t.id),
            'source_tender_id': t.source_tender_id,
            'title': t.title,
            'description': t.description,
            'nmck': float(t.nmck) if t.nmck is not None else None,
            'currency': t.currency,
            'published_at': t.published_at.isoformat() if t.published_at else None,
            'deadline_at': t.deadline_at.isoformat() if t.deadline_at else None,
            'customer_name': t.customer_name,
            'customer_inn': t.customer_inn,
            'platform': t.platform,
            'status': t.status,
            'score': float(t.score) if t.score is not None else None,
            'matched_category_name': None,
            'similarity_score': float(t.similarity_score) if t.similarity_score is not None else None,
            'documents_count': documents_counts.get(t.id, 0),
            'positions_count': positions_counts.get(t.id, 0),
            'suppliers_count': 0,
            'best_margin_percent': float(t.final_margin_percent) if t.final_margin_percent is not None else None,
            'has_decision': t.status in ('READY_FOR_DECISION', 'APPROVED', 'REJECTED', 'NEEDS_MORE_INFO'),
            'created_at': t.created_at.isoformat() if t.created_at else None,
            'updated_at': t.updated_at.isoformat() if t.updated_at else None,
        })

    pages = (total + per_page - 1) // per_page if per_page else 0
    return {'success': True, 'data': items, 'meta': {'page': page, 'per_page': per_page, 'total': total, 'pages': pages}}


@router.patch('/{tender_id}')
async def patch_tender(
    tender_id: uuid.UUID,
    payload: TenderUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    update_data = payload.model_dump(exclude_unset=True)
    status_value = update_data.pop('status', None)
    note = update_data.pop('note', None)

    if status_value:
        previous_status = tender.status
        tender.status = status_value
        db.add(TenderStatusHistory(
            tender_id=tender.id,
            status=status_value,
            previous_status=previous_status,
            note=note or 'Ручное изменение статуса'
        ))

    for field, value in update_data.items():
        setattr(tender, field, value)

    await db.commit()
    return {'success': True, 'data': {'message': 'Тендер обновлён'}}

@router.get('/stats')
async def tender_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count(Tender.id)))).scalar_one()
    by_status_rows = await db.execute(select(Tender.status, func.count(Tender.id)).group_by(Tender.status))
    by_status = {status: count for status, count in by_status_rows.all()}
    return {'success': True, 'data': {
        'total': total,
        'by_status': by_status,
        'by_category': [],
        'avg_processing_time_minutes': 0,
        'approval_rate_percent': 0,
        'avg_margin_percent': 0,
        'total_approved_volume_rub': 0,
    }}


def _serialize_position(position: TenderPosition) -> Dict[str, Any]:
    """Представление позиции тендера для API."""
    return {
        'id': str(position.id),
        'position_number': position.position_number,
        'name': position.name,
        'characteristics': position.characteristics,
        'gost': position.gost,
        'okpd2': position.okpd2,
        'quantity': float(position.quantity),
        'unit': position.unit,
        'is_essential': position.is_essential,
        'notes': position.notes,
    }


def _serialize_requirements(requirements: Optional[TenderRequirements]) -> Optional[Dict[str, Any]]:
    """Представление условий поставки для API."""
    if not requirements:
        return None
    return {
        'delivery_date': requirements.delivery_date.isoformat() if requirements.delivery_date else None,
        'delivery_address': requirements.delivery_address,
        'delivery_conditions': requirements.delivery_conditions,
        'license_required': requirements.license_required,
        'sro_required': requirements.sro_required,
        'security_bid': float(requirements.security_bid) if requirements.security_bid is not None else None,
        'security_contract': float(requirements.security_contract) if requirements.security_contract is not None else None,
        'prepayment_percent': requirements.prepayment_percent,
        'stages_count': requirements.stages_count,
        'special_conditions': requirements.special_conditions or [],
    }


def _serialize_lot_supplier(lot, supplier, best_offer) -> Dict[str, Any]:
    """Представление поставщика лота для API (со статусом и лучшим КП)."""
    margin = None
    if best_offer is not None and best_offer.margin_percent is not None:
        margin = float(best_offer.margin_percent)
    return {
        'id': str(lot.id),
        'supplier_id': str(lot.supplier_id),
        'supplier_name': supplier.name if supplier else '',
        'supplier_email': supplier.email if supplier else '',
        'supplier_website': supplier.website if supplier else '',
        'status': lot.status,
        'priority': lot.priority,
        'source': lot.source,
        'match_relevance': lot.match_relevance,
        'has_cp': best_offer is not None,
        'cp_status': best_offer.status if best_offer else None,
        'cp_margin_percent': margin,
    }


def _serialize_document(document: TenderDocument) -> Dict[str, Any]:
    """Представление документа закупки для API."""
    preview = None
    if document.parsed_text:
        preview = document.parsed_text[:500]
    return {
        'id': str(document.id),
        'filename': document.filename,
        'file_size_bytes': document.file_size_bytes,
        'mime_type': document.mime_type,
        'source_url': document.source_url,
        'parse_status': document.parse_status,
        'parsed_text_preview': preview,
    }


@router.get('/{tender_id}')
async def get_tender(tender_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    t = await db.get(Tender, tender_id)
    if not t:
        raise NotFoundError('Тендер не найден')

    positions_result = await db.execute(
        select(TenderPosition)
        .where(TenderPosition.tender_id == tender_id)
        .order_by(TenderPosition.position_number)
    )
    positions = positions_result.scalars().all()

    documents_result = await db.execute(
        select(TenderDocument)
        .where(TenderDocument.tender_id == tender_id)
        .order_by(TenderDocument.filename)
    )
    documents = documents_result.scalars().all()

    requirements = (await db.execute(
        select(TenderRequirements).where(TenderRequirements.tender_id == tender_id)
    )).scalar_one_or_none()

    lots = (await db.execute(
        select(LotSupplier).where(LotSupplier.tender_id == tender_id).order_by(LotSupplier.priority)
    )).scalars().all()

    suppliers_data: List[Dict[str, Any]] = []
    if lots:
        lot_ids = [lot.id for lot in lots]
        supplier_ids = [lot.supplier_id for lot in lots]

        suppliers_map = {
            supplier.id: supplier
            for supplier in (await db.execute(
                select(Supplier).where(Supplier.id.in_(supplier_ids))
            )).scalars().all()
        }

        offers = (await db.execute(
            select(CommercialOffer)
            .where(CommercialOffer.lot_supplier_id.in_(lot_ids))
        )).scalars().all()
        # Лучшим считаем наиболее полное КП: сначала по статусу
        # (FULL > PARTIAL > NONE), затем по марже. Иначе пустое КП
        # с «маржой» 100% перекрывает реальное предложение.
        status_rank = {'FULL': 0, 'PARTIAL': 1, 'NONE': 2}
        offers.sort(key=lambda o: (
            status_rank.get(o.status, 3),
            -(o.margin_percent if o.margin_percent is not None else float('-inf')),
        ))
        best_offers: Dict[uuid.UUID, CommercialOffer] = {}
        for offer in offers:
            best_offers.setdefault(offer.lot_supplier_id, offer)

        for lot in lots:
            suppliers_data.append(
                _serialize_lot_supplier(lot, suppliers_map.get(lot.supplier_id), best_offers.get(lot.id))
            )

    category = None
    if t.matched_category_id:
        category = await db.get(Category, t.matched_category_id)

    return {'success': True, 'data': {
        'id': str(t.id),
        'source_tender_id': t.source_tender_id,
        'title': t.title,
        'description': t.description,
        'nmck': float(t.nmck) if t.nmck is not None else None,
        'currency': t.currency,
        'published_at': t.published_at.isoformat() if t.published_at else None,
        'deadline_at': t.deadline_at.isoformat() if t.deadline_at else None,
        'customer_name': t.customer_name,
        'customer_inn': t.customer_inn,
        'customer_kpp': t.customer_kpp,
        'platform': t.platform,
        'source_url': t.source_url,
        'status': t.status,
        'score': float(t.score) if t.score is not None else None,
        'score_components': t.score_components,
        'matched_category_id': str(t.matched_category_id) if t.matched_category_id else None,
        'matched_category_name': category.name if category else None,
        'similarity_score': float(t.similarity_score) if t.similarity_score is not None else None,
        'risk_level': t.risk_level,
        'risk_details': t.risk_details,
        'processing_error': t.processing_error,
        'created_at': t.created_at.isoformat() if t.created_at else None,
        'updated_at': t.updated_at.isoformat() if t.updated_at else None,
        'source': None,
        'status_history': [],
        'matched_categories': [],
        'structured_data': t.structured_data,
        'positions': [_serialize_position(p) for p in positions],
        'requirements': _serialize_requirements(requirements),
        'documents': [_serialize_document(d) for d in documents],
        'suppliers': suppliers_data,
        'selected_supplier_id': str(t.selected_supplier_id) if t.selected_supplier_id else None,
        'final_margin_absolute': float(t.final_margin_absolute) if t.final_margin_absolute is not None else None,
        'final_margin_percent': float(t.final_margin_percent) if t.final_margin_percent is not None else None,
    }}



@router.post('', status_code=status.HTTP_201_CREATED)
async def create_tender(payload: TenderCreateRequest, db: AsyncSession = Depends(get_db)):
    source = await db.get(TenderSource, MANUAL_SOURCE_ID)
    if not source:
        raise NotFoundError('Источник для ручного ввода не найден')

    tender = Tender(
        source_id=MANUAL_SOURCE_ID,
        source_tender_id=uuid.uuid4().hex,
        title=payload.title,
        description=payload.description,
        nmck=payload.nmck,
        published_at=payload.published_at,
        deadline_at=payload.deadline_at,
        customer_name=payload.customer_name,
        customer_inn=payload.customer_inn,
        customer_kpp=payload.customer_kpp,
        platform=payload.platform,
        source_url=payload.source_url,
        status='NEW'
    )
    db.add(tender)
    await db.flush()

    history = TenderStatusHistory(tender_id=tender.id, status='NEW', previous_status=None, note='Создан вручную')
    db.add(history)
    await db.commit()
    await db.refresh(tender)

    if not payload.skip_auto_processing:
        task = Task(
            task_type='PROCESS_TENDER',
            status='PENDING',
            entity_type='tender',
            entity_id=tender.id,
            progress_percent=0.0,
            input_data={'tender_id': str(tender.id)}
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        celery_result = process_tender_task.delay(str(task.id))
        task.celery_task_id = celery_result.id
        await db.commit()
        return {'success': True, 'data': {'id': str(tender.id), 'title': tender.title, 'status': tender.status, 'task_id': str(task.id)}}

    return {'success': True, 'data': {'id': str(tender.id), 'title': tender.title, 'status': tender.status}}

@router.post('/{tender_id}/reprocess', status_code=status.HTTP_202_ACCEPTED)
async def reprocess_tender(tender_id: uuid.UUID, payload: ReprocessRequest, db: AsyncSession = Depends(get_db)):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    task = Task(
        task_type='PROCESS_TENDER',
        status='PENDING',
        entity_type='tender',
        entity_id=tender.id,
        progress_percent=0.0,
        input_data={'tender_id': str(tender_id), 'from_stage': payload.from_stage}
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    celery_result = process_tender_task.delay(str(task.id))
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

@router.post('/{tender_id}/search-suppliers', status_code=status.HTTP_202_ACCEPTED)
async def search_suppliers(tender_id: uuid.UUID, payload: SearchSuppliersRequest, db: AsyncSession = Depends(get_db)):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    task = Task(
        task_type='SEARCH_SUPPLIERS',
        status='PENDING',
        entity_type='tender',
        entity_id=tender_id,
        progress_percent=0.0,
        input_data={
            'tender_id': str(tender_id),
            'max_suppliers': payload.max_suppliers,
            'channels': payload.channels,
            'priority_order': payload.priority_order,
        }
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    celery_result = search_suppliers_task.delay(str(task.id))
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

@router.get('/{tender_id}/supplier-search-results')
async def get_supplier_search_results(tender_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Возвращает результаты последнего поиска поставщиков для тендера."""
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    # Находим последнюю завершённую задачу поиска поставщиков
    task_result = await db.execute(
        select(Task).where(
            Task.entity_type == 'tender',
            Task.entity_id == tender_id,
            Task.task_type == 'SEARCH_SUPPLIERS',
            Task.status == 'COMPLETED'
        ).order_by(Task.created_at.desc()).limit(1)
    )
    task = task_result.scalar_one_or_none()
    if not task:
        return {
            'success': True,
            'data': {
                'tender_id': str(tender_id),
                'status': 'SEARCH_IN_PROGRESS',
                'searched_at': None,
                'search_queries_used': [],
                'total_found': 0,
                'after_dedup': 0,
                'after_priority_filter': 0,
                'suppliers': [],
            }
        }

    output = task.output_data or {}
    return {
        'success': True,
        'data': {
            'tender_id': str(tender_id),
            'status': 'SUPPLIERS_FOUND' if output.get('results') else 'NO_SUPPLIERS_FOUND',
            'searched_at': task.completed_at.isoformat() if task.completed_at else None,
            'search_queries_used': output.get('search_queries_used', []),
            'total_found': output.get('total_found', 0),
            'after_dedup': output.get('after_dedup', 0),
            'after_priority_filter': output.get('after_priority_filter', 0),
            'suppliers': output.get('results', []),
        }
    }

@router.post('/{tender_id}/supplier-search-results/confirm')
async def confirm_suppliers(
    tender_id: uuid.UUID,
    payload: ConfirmSuppliersRequest,
    db: AsyncSession = Depends(get_db)
):
    """Подтверждает выбранных поставщиков и привязывает их к лоту."""
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    linked = 0
    created = 0

    # Существующие поставщики
    from app.models.lot_supplier import LotSupplier
    from app.models.supplier import Supplier
    for sid in payload.supplier_ids:
        supplier = await db.get(Supplier, sid)
        if not supplier:
            continue
        existing_lot = await db.execute(
            select(LotSupplier).where(
                LotSupplier.tender_id == tender_id,
                LotSupplier.supplier_id == sid
            )
        )
        if existing_lot.scalar_one_or_none():
            continue
        lot = LotSupplier(
            tender_id=tender_id,
            supplier_id=sid,
            status='PENDING',
            priority=0,
            source='manual',
            match_relevance=None,
        )
        db.add(lot)
        linked += 1

    # Новые поставщики
    for new_supplier in payload.new_suppliers:
        supplier = Supplier(
            name=new_supplier.name,
            type=new_supplier.type,
            website=new_supplier.website,
            email=new_supplier.email,
            phone=new_supplier.phone,
            telegram=new_supplier.telegram,
            whatsapp=new_supplier.whatsapp,
            inn=new_supplier.inn,
            kpp=new_supplier.kpp,
            ogrn=new_supplier.ogrn,
            legal_address=new_supplier.legal_address,
            contact_persons=[cp.model_dump() for cp in new_supplier.contact_persons],
            tags=new_supplier.tags,
            notes=new_supplier.notes,
        )
        db.add(supplier)
        await db.flush()
        lot = LotSupplier(
            tender_id=tender_id,
            supplier_id=supplier.id,
            status='PENDING',
            priority=0,
            source='manual',
            match_relevance=None,
        )
        db.add(lot)
        created += 1
        linked += 1

    await db.commit()
    return {
        'success': True,
        'data': {
            'tender_id': str(tender_id),
            'suppliers_linked': linked,
            'suppliers_created': created,
        }
    }



@router.post('/{tender_id}/run-pipeline', status_code=status.HTTP_202_ACCEPTED)
async def run_pipeline(
    tender_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Запускает полный конвейер для тендера: обработка -> генерация запросов -> поиск поставщиков -> сбор email -> создание черновиков."""
    from app.models.outgoing_draft import OutgoingDraft
    from app.services.pipeline_service import run_full_pipeline_for_tender
    from app.workers.tasks import run_full_pipeline_task

    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    task = Task(
        task_type='PIPELINE',
        status='PENDING',
        entity_type='tender',
        entity_id=tender_id,
        progress_percent=0.0,
        input_data={'tender_id': str(tender_id)}
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    celery_result = run_full_pipeline_task.delay(str(task.id))
    task.celery_task_id = celery_result.id
    await db.commit()

    return {
        'success': True,
        'data': {
            'task_id': str(task.id),
            'status': 'ACCEPTED',
            'estimated_time_seconds': 180,
            'check_url': f'/api/v1/tasks/{task.id}'
        }
    }


@router.get('/{tender_id}/pipeline-steps')
async def get_pipeline_steps(
    tender_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Возвращает текущие шаги пайплайна для тендера."""
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    task_result = await db.execute(
        select(Task).where(
            Task.entity_type == 'tender',
            Task.entity_id == tender_id,
            Task.task_type == 'PIPELINE',
        ).order_by(Task.created_at.desc()).limit(1)
    )
    task = task_result.scalar_one_or_none()

    steps = task.output_data.get('steps', []) if task and task.output_data else []

    return {
        'success': True,
        'data': {
            'task_id': str(task.id) if task else None,
            'status': task.status if task else None,
            'progress_percent': task.progress_percent if task else 0,
            'steps': steps,
            'result_summary': task.result_summary if task else None,
            'error_message': task.error_message if task else None,
        }
    }


@router.get('/{tender_id}/drafts')
async def list_drafts(
    tender_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Возвращает черновики писем для тендера."""
    from app.models.outgoing_draft import OutgoingDraft

    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    result = await db.execute(
        select(OutgoingDraft).where(
            OutgoingDraft.tender_id == tender_id
        ).order_by(OutgoingDraft.created_at.desc())
    )
    drafts = result.scalars().all()

    return {
        'success': True,
        'data': {
            'tender_id': str(tender_id),
            'drafts': [
                {
                    'id': str(d.id),
                    'supplier_website': d.supplier_website,
                    'supplier_name': d.supplier_name,
                    'email': d.email,
                    'subject': d.subject,
                    'body_text': d.body_text,
                    'status': d.status,
                    'metadata': d.metadata_json,
                    'created_at': d.created_at.isoformat() if d.created_at else None,
                }
                for d in drafts
            ]
        }
    }


@router.post('/{tender_id}/drafts/send', status_code=status.HTTP_202_ACCEPTED)
async def send_drafts(
    tender_id: uuid.UUID,
    payload: SendDraftsRequest | None = None,
    db: AsyncSession = Depends(get_db)
):
    """Отправляет выбранные черновики (draft_ids) поставщикам."""
    from app.models.outgoing_draft import OutgoingDraft
    from app.services.email_service import send_email
    from app.models.communication import Communication
    from app.models.lot_supplier import LotSupplier
    from app.models.supplier import Supplier

    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    draft_ids = payload.draft_ids if payload else []
    # Пустой список = ничего не отправляем (безопасное поведение)
    if not draft_ids:
        return {
            'success': True,
            'data': {
                'tender_id': str(tender_id),
                'sent_count': 0,
                'failed_count': 0,
                'details': [],
                'message': 'Нет выбранных черновиков для отправки',
            }
        }

    sent_count = 0
    failed_count = 0
    sent_details = []

    for draft_id in draft_ids:
        try:
            draft_uuid = uuid.UUID(str(draft_id))
        except (ValueError, TypeError):
            continue
        draft = await db.get(OutgoingDraft, draft_uuid)
        if not draft or draft.tender_id != tender_id or draft.status != 'draft':
            continue

        # Проверяем/создаём поставщика
        supplier_result = await db.execute(
            select(Supplier).where(Supplier.email == draft.email.lower())
        )
        supplier = supplier_result.scalar_one_or_none()

        if not supplier:
            supplier = Supplier(
                name=draft.supplier_name or draft.email.split('@')[0],
                type='unknown',
                website=draft.supplier_website,
                email=draft.email.lower(),
                tags=['auto-found'],
            )
            db.add(supplier)
            await db.flush()

        # Привязываем к лоту
        lot_result = await db.execute(
            select(LotSupplier).where(
                LotSupplier.tender_id == tender_id,
                LotSupplier.supplier_id == supplier.id
            )
        )
        lot = lot_result.scalar_one_or_none()
        if not lot:
            lot = LotSupplier(
                tender_id=tender_id,
                supplier_id=supplier.id,
                status='CP_REQUESTED',
                source='pipeline',
            )
            db.add(lot)
            await db.flush()

        # Отправляем email
        sent, message_id = await send_email(
            to_address=draft.email,
            subject=draft.subject,
            body_text=draft.body_text,
            body_html=None,
            db=db
        )

        if not sent:
            failed_count += 1
            continue

        # Создаём Communication
        comm = Communication(
            lot_supplier_id=lot.id,
            tender_id=tender_id,
            direction='outgoing',
            channel='email',
            subject=draft.subject,
            body_text=draft.body_text,
            message_type='cp_request',
            external_id=message_id,
            sent_at=datetime.now(timezone.utc),
        )
        db.add(comm)

        # Обновляем статус черновика
        draft.status = 'sent'
        draft.sent_at = datetime.now(timezone.utc)
        draft.sent_external_id = message_id

        sent_count += 1
        sent_details.append({
            'draft_id': str(draft.id),
            'email': draft.email,
            'supplier_id': str(supplier.id),
            'message_id': message_id,
        })

    await db.commit()

    return {
        'success': True,
        'data': {
            'tender_id': str(tender_id),
            'sent_count': sent_count,
            'failed_count': failed_count,
            'details': sent_details,
        }
    }
