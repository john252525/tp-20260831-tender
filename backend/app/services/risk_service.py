from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tender import Tender
from app.models.commercial_offer import CommercialOffer, OfferPosition
from app.models.tender_requirements import TenderRequirements
from app.models.supplier import Supplier
from app.models.lot_supplier import LotSupplier
from app.models.setting import Setting

async def calculate_risk(tender_id, supplier_id=None, offer_id=None, db: AsyncSession = None) -> Dict[str, Any]:
    tender = await db.get(Tender, tender_id)
    if not tender:
        return {'level': 'UNKNOWN', 'factors': []}

    factors = []
    offer = None
    if offer_id:
        offer = await db.get(CommercialOffer, offer_id)
    elif supplier_id:
        lot = (await db.execute(
            select(LotSupplier).where(LotSupplier.tender_id == tender_id, LotSupplier.supplier_id == supplier_id)
        )).scalar_one_or_none()
        if lot:
            offer = (await db.execute(
                select(CommercialOffer).where(CommercialOffer.lot_supplier_id == lot.id).order_by(CommercialOffer.margin_percent.desc()).limit(1)
            )).scalar_one_or_none()

    margin_percent = offer.margin_percent if offer and offer.margin_percent is not None else None
    if margin_percent is not None:
        min_margin = 15.0
        if margin_percent < min_margin:
            factors.append({'type': 'price', 'level': 'HIGH', 'description': f'Маржа {margin_percent:.1f}% ниже порога {min_margin}%'})
        elif margin_percent < min_margin * 1.5:
            factors.append({'type': 'price', 'level': 'MEDIUM', 'description': f'Маржа {margin_percent:.1f}% близка к порогу'})
        else:
            factors.append({'type': 'price', 'level': 'LOW', 'description': 'Маржа достаточна'})

    if tender.deadline_at and offer:
        days_until_deadline = (tender.deadline_at - datetime.now(timezone.utc)).days
        delivery_days = 0
        positions = (await db.execute(
            select(OfferPosition).where(OfferPosition.commercial_offer_id == offer.id)
        )).scalars().all()
        if positions:
            delivery_days = max((p.delivery_days or 0) for p in positions)
        reserve = days_until_deadline - delivery_days
        if reserve < 0:
            factors.append({'type': 'deadline', 'level': 'HIGH', 'description': 'Срок поставки превышает дедлайн'})
        elif reserve < 7:
            factors.append({'type': 'deadline', 'level': 'HIGH', 'description': f'Запас всего {reserve} дн.'})
        elif reserve < 14:
            factors.append({'type': 'deadline', 'level': 'MEDIUM', 'description': f'Запас {reserve} дн.'})
        else:
            factors.append({'type': 'deadline', 'level': 'LOW', 'description': f'Запас {reserve} дн. достаточен'})

    if supplier_id:
        supplier = await db.get(Supplier, supplier_id)
        if supplier:
            if supplier.successful_deals == 0 and supplier.total_lots == 0:
                factors.append({'type': 'supplier', 'level': 'HIGH', 'description': 'Поставщик новый, без истории'})
            elif supplier.successful_deals == 0:
                factors.append({'type': 'supplier', 'level': 'MEDIUM', 'description': 'Поставщик без успешных сделок'})
            else:
                factors.append({'type': 'supplier', 'level': 'LOW', 'description': 'Есть успешные сделки'})

    levels = [f['level'] for f in factors]
    if 'HIGH' in levels:
        final_level = 'HIGH'
    elif levels.count('MEDIUM') >= 2:
        final_level = 'HIGH'
    elif 'MEDIUM' in levels:
        final_level = 'MEDIUM'
    else:
        final_level = 'LOW'

    return {'level': final_level, 'factors': factors}
