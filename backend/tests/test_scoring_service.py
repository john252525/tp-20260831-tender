"""Тесты расчёта скоринга тендера (в первую очередь — маржинальности)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scoring_service import _margin_to_score


def test_margin_score_below_threshold():
    """Маржа ниже порога даёт балл ниже 60."""
    assert _margin_to_score(0.0, 15.0) == 0.0
    assert _margin_to_score(7.5, 15.0) == 30.0
    assert _margin_to_score(14.9, 15.0) < 60.0


def test_margin_score_at_threshold_is_60():
    """Маржа на уровне порога — ровно 60 баллов (граница выгодности)."""
    assert _margin_to_score(15.0, 15.0) == 60.0


def test_margin_score_double_threshold_is_100():
    """Двукратное превышение порога — максимум."""
    assert _margin_to_score(30.0, 15.0) == 100.0
    assert _margin_to_score(100.0, 15.0) == 100.0


def test_margin_score_is_monotonic():
    """Балл не убывает с ростом маржи."""
    scores = [_margin_to_score(m, 15.0) for m in range(0, 40)]
    assert scores == sorted(scores)


@pytest.mark.asyncio
async def test_margin_score_prefers_actual_offers():
    """При наличии содержательных КП используется их маржа."""
    from app.services.scoring_service import _calculate_margin_score

    tender = MagicMock()
    tender.id = uuid.uuid4()
    tender.matched_category_id = None

    db = AsyncMock()
    offers_result = MagicMock()
    offers_result.scalars().all.return_value = [25.0, 15.0]
    db.execute = AsyncMock(return_value=offers_result)

    scoring = {'min_margin_percent': 15.0, 'margin_fallback_score': 50}
    score, details = await _calculate_margin_score(tender, db, scoring)

    assert details['margin_source'] == 'offers'
    assert details['margin_percent'] == 25.0
    assert score > 60.0


@pytest.mark.asyncio
async def test_margin_score_falls_back_when_no_data():
    """Без КП и категории берётся значение из настроек."""
    from app.services.scoring_service import _calculate_margin_score

    tender = MagicMock()
    tender.id = uuid.uuid4()
    tender.matched_category_id = None

    db = AsyncMock()
    empty_result = MagicMock()
    empty_result.scalars().all.return_value = []
    db.execute = AsyncMock(return_value=empty_result)

    scoring = {'min_margin_percent': 15.0, 'margin_fallback_score': 50}
    score, details = await _calculate_margin_score(tender, db, scoring)

    assert details['margin_source'] == 'fallback'
    assert score == 50.0


@pytest.mark.asyncio
async def test_margin_score_uses_category_average():
    """Без КП по тендеру берётся средняя маржа по его категории."""
    from app.services.scoring_service import _calculate_margin_score

    tender = MagicMock()
    tender.id = uuid.uuid4()
    tender.matched_category_id = uuid.uuid4()

    db = AsyncMock()
    by_tender = MagicMock()
    by_tender.scalars().all.return_value = []
    by_category = MagicMock()
    by_category.scalars().all.return_value = [20.0, 30.0, 40.0]
    db.execute = AsyncMock(side_effect=[by_tender, by_category])

    scoring = {'min_margin_percent': 15.0, 'margin_fallback_score': 50}
    score, details = await _calculate_margin_score(tender, db, scoring)

    assert details['margin_source'] == 'category'
    assert details['margin_percent'] == 30.0
