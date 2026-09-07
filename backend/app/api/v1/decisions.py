import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, ConflictError
from app.models.tender import Tender
from app.models.decision import Decision
from app.models.lot_supplier import LotSupplier
from app.models.supplier import Supplier
from app.models.commercial_offer import CommercialOffer
from app.services.decision_service import get_auto_recommendation
from app.services.risk_service import calculate_risk

router = APIRouter()

@router.get('')
async def list_decisions(
    status: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    min_margin: Optional[float] = Query(None, ge=0),
    sort_by: str = Query('margin_percent', enum=['margin_percent', 'created_at', 'deadline_at']),
    sort_order: str = Query('desc', enum=['asc', 'desc']),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(Tender)
    count_query = select(func.count(Tender.id))
    conditions = []

    if status:
        statuses = [s.strip() for s in status.split(',') if s.strip()]
        conditions.append(Tender.status.in_(statuses))
    else:
        conditions.append(Tender.status.in_(['READY_FOR_DECISION', 'APPROVED', 'REJECTED', 'NEEDS_MORE_INFO']))

    if risk_level:
        levels = [l.strip() for l in risk_level.split(',') if l.strip()]
        conditions.append(Tender.risk_level.in_(levels))

    if min_margin is not None:
        conditions.append(Tender.final_margin_percent >= min_margin)

    for cond in conditions:
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = (await db.execute(count_query)).scalar_one()

    # Сортировка: margin_percent -> final_margin_percent, deadline_at, created_at
    if sort_by == 'margin_percent':
        sort_column = Tender.final_margin_percent
    elif sort_by == 'deadline_at':
        sort_column = Tender.deadline_at
    else:
        sort_column = Tender.created_at

    if sort_order == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    query = query.offset((page - 1) * per_page).limit(per_page)
    tenders = (await db.execute(query)).scalars().all()

    items = []
    for tender in tenders:
        rec = await get_auto_recommendation(str(tender.id), db)

        best_supplier_id_str = rec.get('best_supplier_id')
        best_offer_id_str = rec.get('best_offer_id')

        try:
            best_supplier_uuid = uuid.UUID(best_supplier_id_str) if best_supplier_id_str else None
        except (ValueError, TypeError):
            best_supplier_uuid = None
        try:
            best_offer_uuid = uuid.UUID(best_offer_id_str) if best_offer_id_str else None
        except (ValueError, TypeError):
            best_offer_uuid = None

        risk = await calculate_risk(
            str(tender.id),
            supplier_id=best_supplier_uuid,
            offer_id=best_offer_uuid,
            db=db
        )

        supplier_name = ''
        final_price = None
        if best_offer_uuid:
            best_offer = await db.get(CommercialOffer, best_offer_uuid)
            if best_offer:
                final_price = float(best_offer.total_cost_with_all) if best_offer.total_cost_with_all is not None else None
        if best_supplier_uuid:
            supplier = await db.get(Supplier, best_supplier_uuid)
            if supplier:
                supplier_name = supplier.name

        # Сбор альтернативных поставщиков (N+1: TODO оптимизировать в следующем этапе)
        alternative_suppliers = []
        lots = (await db.execute(
            select(LotSupplier).where(LotSupplier.tender_id == tender.id)
        )).scalars().all()
        for lot in lots:
            if best_supplier_uuid and lot.supplier_id == best_supplier_uuid:
                continue
            alt_offer = (await db.execute(
                select(CommercialOffer).where(
                    CommercialOffer.lot_supplier_id == lot.id
                ).order_by(CommercialOffer.margin_percent.desc()).limit(1)
            )).scalar_one_or_none()
            if alt_offer and alt_offer.margin_percent is not None:
                alt_supplier = await db.get(Supplier, lot.supplier_id)
                alternative_suppliers.append({
                    'id': str(lot.supplier_id),
                    'name': alt_supplier.name if alt_supplier else '',
                    'margin_percent': alt_offer.margin_percent,
                })

        items.append({
            'tender_id': str(tender.id),
            'tender_title': tender.title,
            'nmck': float(tender.nmck) if tender.nmck else None,
            'deadline_at': tender.deadline_at.isoformat() if tender.deadline_at else None,
            'best_supplier': {
                'id': best_supplier_id_str,
                'name': supplier_name,
                'offer_id': best_offer_id_str,
                'final_price': final_price,
                'margin_percent': rec.get('margin_percent'),
            },
            'alternative_suppliers': alternative_suppliers,
            'risk_assessment': {'level': risk['level'], 'factors': risk['factors']},
            'auto_recommendation': rec.get('recommendation'),
            'status': tender.status,
            'ready_at': tender.updated_at.isoformat(),
        })

    pages = (total + per_page - 1) // per_page
    return {'success': True, 'data': items, 'meta': {'page': page, 'per_page': per_page, 'total': total, 'pages': pages}}

@router.post('/{tender_id}/approve')
async def approve_decision(tender_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(get_db)):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')
    if tender.status != 'READY_FOR_DECISION':
        raise ConflictError('Тендер не в статусе READY_FOR_DECISION')

    chosen_supplier_id = payload.get('chosen_supplier_id')
    chosen_offer_id = payload.get('chosen_offer_id')
    comment = payload.get('comment', '')

    if chosen_supplier_id:
        supplier = await db.get(Supplier, uuid.UUID(chosen_supplier_id))
        if not supplier:
            raise NotFoundError('Поставщик не найден')
    if chosen_offer_id:
        offer = await db.get(CommercialOffer, uuid.UUID(chosen_offer_id))
        if not offer:
            raise NotFoundError('КП не найдено')

    decision = Decision(
        tender_id=tender_id,
        decision='APPROVED',
        chosen_supplier_id=uuid.UUID(chosen_supplier_id) if chosen_supplier_id else None,
        chosen_offer_id=uuid.UUID(chosen_offer_id) if chosen_offer_id else None,
        margin_at_decision=offer.margin_percent if offer else None,
        risk_level_at_decision=None,
        reason=comment,
    )
    db.add(decision)
    tender.status = 'APPROVED'
    tender.selected_supplier_id = uuid.UUID(chosen_supplier_id) if chosen_supplier_id else None
    tender.final_margin_percent = offer.margin_percent if offer else None
    await db.commit()
    return {'success': True, 'data': {'message': 'Тендер одобрен'}}

@router.post('/{tender_id}/reject')
async def reject_decision(tender_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(get_db)):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')
    if tender.status != 'READY_FOR_DECISION':
        raise ConflictError('Тендер не в статусе READY_FOR_DECISION')

    reason = payload.get('reason', 'low_margin')
    comment = payload.get('comment', '')
    decision = Decision(
        tender_id=tender_id,
        decision='REJECTED',
        reason=f'{reason}: {comment}' if comment else reason,
    )
    db.add(decision)
    tender.status = 'REJECTED'
    await db.commit()
    return {'success': True, 'data': {'message': 'Тендер отклонён'}}

@router.post('/{tender_id}/request-info')
async def request_info(tender_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(get_db)):
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise NotFoundError('Тендер не найден')

    instructions = payload.get('instructions', '')
    decision = Decision(
        tender_id=tender_id,
        decision='NEEDS_MORE_INFO',
        reason=instructions,
    )
    db.add(decision)
    tender.status = 'NEEDS_MORE_INFO'
    await db.commit()
    return {'success': True, 'data': {'message': 'Запрос дополнительной информации создан'}}
