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

    # 1. Маржинальность Sm.
    # Источники по убыванию достоверности: фактические КП по этому тендеру,
    # затем средняя маржа по категории (исторические КП), затем значение из настроек.
    margin_score, margin_details = await _calculate_margin_score(tender, db, scoring)

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
    components.update(margin_details)
    return round(total, 2), components


def _margin_to_score(margin_percent: float, min_margin_percent: float) -> float:
    """Переводит маржу в балл 0..100.

    Порог из настроек соответствует 60 баллам (тендер считается выгодным),
    вдвое большая маржа — 100 баллам. Ниже порога балл падает линейно.
    """
    if margin_percent <= 0:
        return 0.0
    threshold = max(min_margin_percent, 1.0)
    if margin_percent >= threshold * 2:
        return 100.0
    if margin_percent >= threshold:
        # 60..100 баллов на отрезке [порог; 2*порог]
        ratio = (margin_percent - threshold) / threshold
        return round(60.0 + 40.0 * ratio, 2)
    # 0..60 баллов на отрезке [0; порог]
    return round(60.0 * (margin_percent / threshold), 2)


async def _calculate_margin_score(
    tender: Tender,
    db: AsyncSession,
    scoring: Dict[str, Any],
) -> tuple[float, Dict[str, Any]]:
    """Оценивает маржинальность тендера по фактическим данным.

    Фактические КП по тендеру точнее любой оценки, поэтому используются первыми.
    Если КП ещё нет, берётся средняя маржа по категории тендера (из прошлых
    закупок) — это рыночный ориентир. И только при полном отсутствии данных
    берётся значение из настроек.
    """
    from app.models.commercial_offer import CommercialOffer

    min_margin = float(scoring.get('min_margin_percent', 15.0) or 15.0)

    # 1) Фактические КП по этому тендеру
    # Пустые КП (статус NONE) не содержат цен и дают фиктивную маржу —
    # в расчёте участвуют только содержательные предложения.
    offers = (await db.execute(
        select(CommercialOffer.margin_percent).where(
            CommercialOffer.tender_id == tender.id,
            CommercialOffer.margin_percent.is_not(None),
            CommercialOffer.status.in_(('FULL', 'PARTIAL')),
        )
    )).scalars().all()

    if offers:
        best_margin = max(float(m) for m in offers)
        return _margin_to_score(best_margin, min_margin), {
            'margin_source': 'offers',
            'margin_percent': round(best_margin, 2),
            'margin_offers_count': len(offers),
        }

    # 2) Средняя маржа по категории тендера
    if tender.matched_category_id:
        category_margins = (await db.execute(
            select(CommercialOffer.margin_percent).where(
                CommercialOffer.margin_percent.is_not(None),
                CommercialOffer.status.in_(('FULL', 'PARTIAL')),
                CommercialOffer.tender_id.in_(
                    select(Tender.id).where(Tender.matched_category_id == tender.matched_category_id)
                ),
            )
        )).scalars().all()
        if category_margins:
            avg_margin = sum(float(m) for m in category_margins) / len(category_margins)
            return _margin_to_score(avg_margin, min_margin), {
                'margin_source': 'category',
                'margin_percent': round(avg_margin, 2),
                'margin_offers_count': len(category_margins),
            }

    # 3) Данных нет — значение из настроек
    fallback = float(scoring['margin_fallback_score'])
    return fallback, {'margin_source': 'fallback', 'margin_percent': None}

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
