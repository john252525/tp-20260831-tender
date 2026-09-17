"""Тесты пересчёта статуса тендера по фактическим данным."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.commercial_offer import CommercialOffer
from app.models.lot_supplier import LotSupplier
from app.models.tender import Tender
from app.services.tender_status_service import (
    _risk_allowed,
    recalculate_tender_status,
)


def _tender(status='SCORED'):
    return Tender(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_tender_id='test',
        title='Тестовый тендер',
        description='Описание',
        nmck=1000000,
        status=status,
    )


def _lot(tender_id, status='PENDING'):
    return LotSupplier(
        id=uuid.uuid4(),
        tender_id=tender_id,
        supplier_id=uuid.uuid4(),
        status=status,
        source='manual',
    )


def _offer(lot_id, tender_id, status='FULL', coverage=100.0, margin=25.0):
    offer = CommercialOffer(
        id=uuid.uuid4(),
        lot_supplier_id=lot_id,
        tender_id=tender_id,
        status=status,
        coverage=coverage,
        margin_percent=margin,
        margin_absolute=250000,
    )
    return offer


def test_risk_allowed_thresholds():
    assert _risk_allowed('LOW', 'MEDIUM')
    assert _risk_allowed('MEDIUM', 'MEDIUM')
    assert not _risk_allowed('HIGH', 'MEDIUM')


@pytest.mark.asyncio
async def test_manual_status_is_not_overwritten():
    """Решение человека (APPROVED/REJECTED) пересчёт не трогает."""
    tender = _tender(status='APPROVED')
    db = AsyncMock()
    db.get = AsyncMock(return_value=tender)

    result = await recalculate_tender_status(tender.id, db)

    assert result == 'APPROVED'


@pytest.mark.asyncio
async def test_no_lots_sets_new():
    tender = _tender(status='SCORED')
    db = AsyncMock()
    db.get = AsyncMock(return_value=tender)
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = []
    db.execute = AsyncMock(return_value=lots_result)

    result = await recalculate_tender_status(tender.id, db)

    assert result == 'NEW'


@pytest.mark.asyncio
async def test_requested_cp_without_offers():
    tender = _tender(status='SCORED')
    lot = _lot(tender.id, status='CP_REQUESTED')

    db = AsyncMock()
    db.get = AsyncMock(return_value=tender)
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot]
    offers_result = MagicMock()
    offers_result.scalars().all.return_value = []
    db.execute = AsyncMock(side_effect=[lots_result, offers_result])

    result = await recalculate_tender_status(tender.id, db)

    assert result == 'CP_REQUESTED'


@pytest.mark.asyncio
async def test_full_offer_above_threshold_ready_for_decision():
    """Полное КП с маржой выше порога — тендер готов к решению."""
    tender = _tender(status='SCORED')
    lot = _lot(tender.id, status='CP_REQUESTED')
    offer = _offer(lot.id, tender.id, status='FULL', coverage=100.0, margin=30.0)

    db = AsyncMock()
    db.get = AsyncMock(return_value=tender)
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot]
    offers_result = MagicMock()
    offers_result.scalars().all.return_value = [offer]
    db.execute = AsyncMock(side_effect=[lots_result, offers_result])

    with patch('app.services.tender_status_service.get_section_settings', new_callable=AsyncMock) as mock_settings, \
         patch('app.services.tender_status_service.calculate_risk', new_callable=AsyncMock) as mock_risk:
        mock_settings.return_value = {'min_margin_percent': 15.0, 'max_risk_level': 'MEDIUM'}
        mock_risk.return_value = {'level': 'LOW', 'factors': []}
        result = await recalculate_tender_status(tender.id, db)

    assert result == 'READY_FOR_DECISION'
    assert tender.final_margin_percent == 30.0
    assert tender.risk_level == 'LOW'
    # Лот переведён в состояние «КП получено»
    assert lot.status == 'CP_RECEIVED'


@pytest.mark.asyncio
async def test_full_offer_below_threshold_stays_fully_received():
    """Маржа ниже порога — тендер не отдаётся человеку."""
    tender = _tender(status='SCORED')
    lot = _lot(tender.id, status='CP_REQUESTED')
    offer = _offer(lot.id, tender.id, status='FULL', coverage=100.0, margin=5.0)

    db = AsyncMock()
    db.get = AsyncMock(return_value=tender)
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot]
    offers_result = MagicMock()
    offers_result.scalars().all.return_value = [offer]
    db.execute = AsyncMock(side_effect=[lots_result, offers_result])

    with patch('app.services.tender_status_service.get_section_settings', new_callable=AsyncMock) as mock_settings, \
         patch('app.services.tender_status_service.calculate_risk', new_callable=AsyncMock) as mock_risk:
        mock_settings.return_value = {'min_margin_percent': 15.0, 'max_risk_level': 'MEDIUM'}
        mock_risk.return_value = {'level': 'LOW', 'factors': []}
        result = await recalculate_tender_status(tender.id, db)

    assert result == 'CP_FULLY_RECEIVED'


@pytest.mark.asyncio
async def test_high_risk_above_threshold_is_not_auto_ready():
    """Высокий риск при достаточной марже не отдаётся автоматически."""
    tender = _tender(status='SCORED')
    lot = _lot(tender.id, status='CP_REQUESTED')
    offer = _offer(lot.id, tender.id, status='FULL', coverage=100.0, margin=40.0)

    db = AsyncMock()
    db.get = AsyncMock(return_value=tender)
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot]
    offers_result = MagicMock()
    offers_result.scalars().all.return_value = [offer]
    db.execute = AsyncMock(side_effect=[lots_result, offers_result])

    with patch('app.services.tender_status_service.get_section_settings', new_callable=AsyncMock) as mock_settings, \
         patch('app.services.tender_status_service.calculate_risk', new_callable=AsyncMock) as mock_risk:
        mock_settings.return_value = {'min_margin_percent': 15.0, 'max_risk_level': 'MEDIUM'}
        mock_risk.return_value = {'level': 'HIGH', 'factors': []}
        result = await recalculate_tender_status(tender.id, db)

    assert result == 'CP_FULLY_RECEIVED'


@pytest.mark.asyncio
async def test_partial_offer_gives_partially_received():
    tender = _tender(status='SCORED')
    lot = _lot(tender.id, status='CP_REQUESTED')
    offer = _offer(lot.id, tender.id, status='PARTIAL', coverage=40.0, margin=20.0)

    db = AsyncMock()
    db.get = AsyncMock(return_value=tender)
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot]
    offers_result = MagicMock()
    offers_result.scalars().all.return_value = [offer]
    db.execute = AsyncMock(side_effect=[lots_result, offers_result])

    result = await recalculate_tender_status(tender.id, db)

    assert result == 'CP_PARTIALLY_RECEIVED'
    assert lot.status == 'CP_RECEIVED'
