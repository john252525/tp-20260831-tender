import structlog
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tender import Tender
from app.models.tender_requirements import TenderRequirements
from app.models.tender_position import TenderPosition
from app.models.setting import Setting

logger = structlog.get_logger()

async def _get_scoring_settings(db: AsyncSession) -> Dict[str, Any]:
    """Возвращает настройки скоринга из БД одним запросом."""
    result = await db.execute(select(Setting).where(Setting.section == 'scoring'))
    settings = result.scalars().all()
    settings_map = {s.key: s.value for s in settings}
    # Применяем дефолты, если каких-то нет
    defaults = {
        'weight_margin': 40,
        'weight_simplicity': 30,
        'weight_volume': 20,
        'weight_competition': 10,
        'volume_thresholds': {'low': 100000, 'medium': 1000000, 'high': 5000000},
        'volume_scores': {'low': 20, 'medium': 50, 'high': 80, 'very_high': 95},
        'default_competition_score': 50,
        'margin_calculation_mode': 'auto',
        'margin_fallback_score': 50,
    }
    for key, value in defaults.items():
        settings_map.setdefault(key, value)
    return settings_map

async def calculate_score(tender: Tender, db: AsyncSession) -> tuple[float, Dict[str, float]]:
    """Вычисляет итоговый скор тендера и возвращает (score, components)."""
    scoring = await _get_scoring_settings(db)

    # 1. Маржинальность Sm (пока fallback, так как нет данных о себестоимости)
    margin_score = float(scoring['margin_fallback_score'])
    # TODO: реализовать расчёт маржи на основе собранных КП и среднерыночных цен

    # 2. Простота исполнения Ss
    simplicity_score = await _calculate_simplicity(tender, db, scoring)

    # 3. Объём Sv
    nmck = float(tender.nmck) if tender.nmck else 0.0
    thresholds = scoring['volume_thresholds']
    volume_scores = scoring['volume_scores']
    if nmck < thresholds['low']:
        volume_score = float(volume_scores['low'])
    elif nmck < thresholds['medium']:
        volume_score = float(volume_scores['medium'])
    elif nmck < thresholds['high']:
        volume_score = float(volume_scores['high'])
    else:
        volume_score = float(volume_scores['very_high'])

    # 4. Конкурентность Sc (пока default, нет истории)
    competition_score = float(scoring['default_competition_score'])
    # TODO: использовать ML и историю, когда будет достаточно данных

    total = (
        float(scoring['weight_margin']) * margin_score
        + float(scoring['weight_simplicity']) * simplicity_score
        + float(scoring['weight_volume']) * volume_score
        + float(scoring['weight_competition']) * competition_score
    ) / 100.0

    components = {
        'margin_score': margin_score,
        'simplicity_score': simplicity_score,
        'volume_score': volume_score,
        'competition_score': competition_score,
    }
    return round(total, 2), components

async def _calculate_simplicity(tender: Tender, db: AsyncSession, scoring: Dict[str, Any]) -> float:
    """Вычисляет скор простоты исполнения на основе позиций и требований."""
    base = 100.0
    deductions = 0.0

    # Количество позиций
    pos_count = (await db.execute(
        select(TenderPosition.id).where(TenderPosition.tender_id == tender.id)
    )).scalars().all()
    n = len(pos_count)
    if n > 10:
        extra = n - 10
        deduction = min(20, (extra // 5) * 5)
        deductions += deduction

    # Срок поставки
    req_result = await db.execute(
        select(TenderRequirements).where(TenderRequirements.tender_id == tender.id)
    )
    req = req_result.scalar_one_or_none()
    if req and req.delivery_date:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        days = (req.delivery_date - now).days
        if days < 7:
            deductions += 30
        elif days < 14:
            deductions += 15

    # Лицензии и СРО (данных о компании нет, считаем что не требуется)
    if req:
        if req.license_required:
            deductions += 50  # компания не имеет лицензии
        if req.sro_required:
            deductions += 50  # компания не в СРО

    # Особые условия
    if req and req.special_conditions:
        deductions += min(20, len(req.special_conditions) * 5)

    # Этапность
    if req and req.stages_count and req.stages_count > 1:
        deductions += min(20, (req.stages_count - 1) * 10)

    return max(0.0, base - deductions)
