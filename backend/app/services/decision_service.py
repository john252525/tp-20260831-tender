from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tender import Tender
from app.models.commercial_offer import CommercialOffer
from app.models.lot_supplier import LotSupplier
from app.models.supplier import Supplier
from app.services.risk_service import calculate_risk

async def get_auto_recommendation(tender_id: str, db: AsyncSession) -> Dict[str, Any]:
    tender = await db.get(Tender, tender_id)
    if not tender:
        return {'recommendation': 'REJECT', 'reason': 'Тендер не найден'}

    # Находим лучший КП
    best_offer = None
    bets_lot_supplier = None
    best_supplier = None
    margin_percent = None
    risk_level = 'LOW'

    lots = (await db.execute(
        select(LotSupplier).where(LotSupplier.tender_id == tender_id)
    )).scalars().all()
    for lot in lots:
        offers = (await db.execute(
            select(CommercialOffer).where(CommercialOffer.lot_supplier_id == lot.id).order_by(CommercialOffer.margin_percent.desc())
        )).scalars().all()
        if offers:
            offer = offers[0]
            if best_offer is None or (offer.margin_percent or 0) > (best_offer.margin_percent or 0):
                best_offer = offer
                bets_lot_supplier = lot
                supplier = await db.get(Supplier, lot.supplier_id)
                best_supplier = supplier
                margin_percent = offer.margin_percent

    if best_offer is None:
        return {'recommendation': 'REJECT', 'reason': 'Нет коммерческих предложений'}

    risk = await calculate_risk(tender_id, supplier_id=best_supplier.id if best_supplier else None, offer_id=best_offer.id, db=db)
    risk_level = risk['level']

    min_margin = 15.0  # TODO: из настроек
    if margin_percent is not None and margin_percent >= min_margin and risk_level in ('LOW', 'MEDIUM'):
        recommendation = 'APPROVE'
    elif margin_percent is not None and margin_percent >= min_margin and risk_level == 'HIGH':
        recommendation = 'REVIEW'
    else:
        recommendation = 'REJECT'

    return {
        'recommendation': recommendation,
        'margin_percent': margin_percent,
        'risk_level': risk_level,
        'best_supplier_id': str(best_supplier.id) if best_supplier else None,
        'best_offer_id': str(best_offer.id) if best_offer else None,
    }
