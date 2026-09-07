import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.commercial_offer import CommercialOffer, OfferPosition
from app.models.tender import Tender
from app.models.supplier import Supplier
from app.models.lot_supplier import LotSupplier
from app.models.task import Task
from app.workers.tasks import parse_cp_task

router = APIRouter()

@router.get('')
async def list_offers(
    tender_id: Optional[uuid.UUID] = Query(None),
    supplier_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    min_margin_percent: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(CommercialOffer)
    count_query = select(func.count(CommercialOffer.id))
    conditions = []
    if tender_id:
        conditions.append(CommercialOffer.tender_id == tender_id)
    if supplier_id:
        lot_ids = select(LotSupplier.id).where(LotSupplier.supplier_id == supplier_id)
        conditions.append(CommercialOffer.lot_supplier_id.in_(lot_ids))
    if status:
        statuses = [s.strip() for s in status.split(',') if s.strip()]
        conditions.append(CommercialOffer.status.in_(statuses))
    if min_margin_percent is not None:
        conditions.append(CommercialOffer.margin_percent >= min_margin_percent)
    for cond in conditions:
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = (await db.execute(count_query)).scalar_one()
    query = query.order_by(CommercialOffer.created_at.desc()).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    offers = result.scalars().all()
    items = []
    for offer in offers:
        lot = await db.get(LotSupplier, offer.lot_supplier_id)
        supplier = await db.get(Supplier, lot.supplier_id) if lot else None
        tender = await db.get(Tender, offer.tender_id)
        items.append({
            'id': str(offer.id),
            'tender_id': str(offer.tender_id),
            'tender_title': tender.title if tender else '',
            'supplier_id': str(supplier.id) if supplier else None,
            'supplier_name': supplier.name if supplier else '',
            'status': offer.status,
            'coverage': offer.coverage,
            'total_cost_with_all': float(offer.total_cost_with_all) if offer.total_cost_with_all is not None else None,
            'margin_absolute': float(offer.margin_absolute) if offer.margin_absolute is not None else None,
            'margin_percent': offer.margin_percent,
            'clarification_needed': offer.clarification_needed,
            'received_at': offer.created_at.isoformat() if offer.created_at else None,
        })
    pages = (total + per_page - 1) // per_page
    return {'success': True, 'data': items, 'meta': {'page': page, 'per_page': per_page, 'total': total, 'pages': pages}}

@router.get('/{cp_id}')
async def get_offer(cp_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    offer = await db.get(CommercialOffer, cp_id)
    if not offer:
        raise NotFoundError('Коммерческое предложение не найдено')
    positions = (await db.execute(
        select(OfferPosition).where(OfferPosition.commercial_offer_id == cp_id)
    )).scalars().all()

    lot_supplier = await db.get(LotSupplier, offer.lot_supplier_id)
    supplier_id = str(lot_supplier.supplier_id) if lot_supplier else None

    return {
        'success': True,
        'data': {
            'id': str(offer.id),
            'tender_id': str(offer.tender_id),
            'supplier_id': supplier_id,
            'source_communication_id': str(offer.source_communication_id) if offer.source_communication_id else None,
            'status': offer.status,
            'coverage': offer.coverage,
            'clarification_needed': offer.clarification_needed,
            'clarification_items': offer.clarification_items,
            'positions': [
                {
                    'id': str(p.id),
                    'tender_position_id': str(p.tender_position_id) if p.tender_position_id else None,
                    'supplier_name': p.supplier_name,
                    'match_type': p.match_type,
                    'match_confidence': p.match_confidence,
                    'price_per_unit': float(p.price_per_unit) if p.price_per_unit is not None else None,
                    'quantity_available': float(p.quantity_available) if p.quantity_available is not None else None,
                    'delivery_days': p.delivery_days,
                    'nds_included': p.nds_included,
                    'nds_rate': p.nds_rate,
                    'total_price': float(p.total_price) if p.total_price is not None else None,
                } for p in positions
            ],
            'delivery_terms': offer.delivery_terms,
            'payment_terms': offer.payment_terms,
            'calculated': {
                'total_positions_cost': float(offer.total_cost) if offer.total_cost is not None else None,
                'delivery_cost': float(offer.delivery_cost) if offer.delivery_cost is not None else None,
                'total_cost_with_delivery': float(offer.total_cost_with_delivery) if offer.total_cost_with_delivery is not None else None,
                'security_bid_cost': None,
                'security_contract_cost': None,
                'total_cost_with_all': float(offer.total_cost_with_all) if offer.total_cost_with_all is not None else None,
                'nmck': None,
                'margin_absolute': float(offer.margin_absolute) if offer.margin_absolute is not None else None,
                'margin_percent': offer.margin_percent,
            },
            'valid_until': offer.valid_until.isoformat() if offer.valid_until else None,
            'raw_text_snippet': offer.raw_text_snippet,
            'received_at': offer.created_at.isoformat() if offer.created_at else None,
            'parsed_at': offer.parsed_at.isoformat() if offer.parsed_at else None,
        }
    }

@router.post('/{cp_id}/reparse', status_code=status.HTTP_202_ACCEPTED)
async def reparse_offer(cp_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    offer = await db.get(CommercialOffer, cp_id)
    if not offer:
        raise NotFoundError('Коммерческое предложение не найдено')

    task = Task(
        task_type='PARSE_CP',
        status='PENDING',
        entity_type='commercial_offer',
        entity_id=cp_id,
        progress_percent=0.0,
        input_data={'cp_id': str(cp_id)}
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    celery_result = parse_cp_task.delay(str(task.id))
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
