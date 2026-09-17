"""Пересчёт статуса тендера по фактическим данным (лоты, КП, переговоры).

Статус тендера нельзя выставлять «вручную» в разных местах: он должен
выводиться из состояния лотов и коммерческих предложений. Иначе тендер
навсегда остаётся в промежуточном статусе и финальный шаг — передача
лучшего предложения человеку (`READY_FOR_DECISION`) — недостижим.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tender import Tender
from app.models.lot_supplier import LotSupplier
from app.models.commercial_offer import CommercialOffer
from app.models.tender_status_history import TenderStatusHistory
from app.services.settings_service import get_section_settings
from app.services.risk_service import calculate_risk

logger = structlog.get_logger()

# Статусы, которые выставляются автоматически и могут быть пересчитаны.
# Ручные решения человека (APPROVED/REJECTED/NEEDS_MORE_INFO) не перетираем.
MANUAL_STATUSES = {'APPROVED', 'REJECTED', 'NEEDS_MORE_INFO'}
# Финальные/служебные статусы, которые пересчёт не трогает.
LOCKED_STATUSES = MANUAL_STATUSES | {'PROCESSING', 'ERROR', 'NOT_RELEVANT'}

DEFAULT_MIN_MARGIN_PERCENT = 15.0
DEFAULT_MAX_RISK_LEVEL = 'MEDIUM'
RISK_ORDER = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2, 'UNKNOWN': 3}


async def _get_thresholds(db: AsyncSession) -> Dict[str, Any]:
    """Пороги принятия решения из настроек (раздел scoring)."""
    scoring = await get_section_settings(db, 'scoring') or {}
    min_margin = scoring.get('min_margin_percent', DEFAULT_MIN_MARGIN_PERCENT)
    max_risk = scoring.get('max_risk_level', DEFAULT_MAX_RISK_LEVEL)
    try:
        min_margin = float(min_margin)
    except (TypeError, ValueError):
        min_margin = DEFAULT_MIN_MARGIN_PERCENT
    if not isinstance(max_risk, str) or max_risk not in RISK_ORDER:
        max_risk = DEFAULT_MAX_RISK_LEVEL
    return {'min_margin_percent': min_margin, 'max_risk_level': max_risk}


def _risk_allowed(risk_level: Optional[str], max_risk_level: str) -> bool:
    """Укладывается ли риск в допустимый порог."""
    if risk_level is None:
        return True
    return RISK_ORDER.get(risk_level, 3) <= RISK_ORDER.get(max_risk_level, 1)


async def recalculate_tender_status(tender_id: uuid.UUID, db: AsyncSession) -> str:
    """Пересчитывает статус тендера по его лотам и КП.

    Возвращает установленный статус. Ручные решения человека не перетираются.
    """
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise ValueError('Тендер не найден')

    if tender.status in LOCKED_STATUSES:
        return tender.status

    lots: List[LotSupplier] = (await db.execute(
        select(LotSupplier).where(LotSupplier.tender_id == tender_id)
    )).scalars().all()

    if not lots:
        # Поставщики ещё не подобраны
        return await _set_status(tender, 'NEW', 'Нет подобранных поставщиков', db)

    offers_by_lot: Dict[uuid.UUID, List[CommercialOffer]] = {}
    if lots:
        offers = (await db.execute(
            select(CommercialOffer)
            .where(CommercialOffer.lot_supplier_id.in_([lot.id for lot in lots]))
            .order_by(CommercialOffer.margin_percent.desc().nullslast())
        )).scalars().all()
        for offer in offers:
            offers_by_lot.setdefault(offer.lot_supplier_id, []).append(offer)

    # Статусы лотов приводим в соответствие с наличием КП
    for lot in lots:
        lot_offers = offers_by_lot.get(lot.id, [])
        if lot_offers and lot.status in ('PENDING', 'CP_REQUESTED'):
            lot.status = 'CP_RECEIVED'
            db.add(lot)

    lots_with_offers = [lot for lot in lots if offers_by_lot.get(lot.id)]
    full_lots = [
        lot for lot in lots_with_offers
        if any(offer.status == 'FULL' and (offer.coverage or 0) >= 100 for offer in offers_by_lot[lot.id])
    ]

    # Нет ни одного КП — значит запросы либо отправлены, либо нет
    if not lots_with_offers:
        awaiting = any(lot.status == 'CP_REQUESTED' for lot in lots)
        status = 'CP_REQUESTED' if awaiting else 'AWAITING_CP'
        return await _set_status(tender, status, 'Коммерческие предложения ещё не получены', db)

    # Все лоты закрыты полными КП — проверяем, можно ли отдавать человеку
    if len(full_lots) == len(lots):
        best_offer = _best_offer(offers_by_lot, full_lots)
        thresholds = await _get_thresholds(db)

        if best_offer is not None and best_offer.margin_percent is not None:
            risk = await calculate_risk(
                str(tender_id),
                supplier_id=None,
                offer_id=best_offer.id,
                db=db,
            )
            risk_level = risk.get('level')
            tender.final_margin_percent = best_offer.margin_percent
            tender.final_margin_absolute = best_offer.margin_absolute
            tender.risk_level = risk_level
            tender.risk_details = risk.get('factors')

            if (
                best_offer.margin_percent >= thresholds['min_margin_percent']
                and _risk_allowed(risk_level, thresholds['max_risk_level'])
            ):
                note = (
                    f'Лучшее предложение: маржа {best_offer.margin_percent:.1f}% '
                    f'(порог {thresholds["min_margin_percent"]:.1f}%), риск {risk_level}'
                )
                return await _set_status(tender, 'READY_FOR_DECISION', note, db)

            note = (
                f'Полные КП получены, но маржа {best_offer.margin_percent:.1f}% '
                f'ниже порога {thresholds["min_margin_percent"]:.1f}%'
            )
            return await _set_status(tender, 'CP_FULLY_RECEIVED', note, db)

        return await _set_status(tender, 'CP_FULLY_RECEIVED', 'Полные КП получены по всем лотам', db)

    # Часть лотов закрыта — считаем покрытие
    if full_lots:
        note = f'Полные КП: {len(full_lots)} из {len(lots)} лотов'
        return await _set_status(tender, 'CP_PARTIALLY_RECEIVED', note, db)

    note = f'КП получены: {len(lots_with_offers)} из {len(lots)} лотов (неполные)'
    return await _set_status(tender, 'CP_PARTIALLY_RECEIVED', note, db)


def _best_offer(
    offers_by_lot: Dict[uuid.UUID, List[CommercialOffer]],
    lots: List[LotSupplier],
) -> Optional[CommercialOffer]:
    """КП с наибольшей маржой среди полностью закрытых лотов."""
    best: Optional[CommercialOffer] = None
    for lot in lots:
        for offer in offers_by_lot.get(lot.id, []):
            if offer.status != 'FULL' or offer.margin_percent is None:
                continue
            if best is None or offer.margin_percent > (best.margin_percent or 0):
                best = offer
    return best


async def _set_status(tender: Tender, status: str, note: str, db: AsyncSession) -> str:
    """Устанавливает статус тендера, если он изменился, и пишет историю."""
    if tender.status == status:
        return status

    previous_status = tender.status
    tender.status = status
    db.add(TenderStatusHistory(
        tender_id=tender.id,
        status=status,
        previous_status=previous_status,
        note=note,
    ))
    await db.flush()
    logger.info(
        'tender_status.recalculated',
        tender_id=str(tender.id),
        previous=previous_status,
        current=status,
    )
    return status
