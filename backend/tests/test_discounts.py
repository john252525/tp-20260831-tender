"""Тесты торга: запрос улучшения цен у поставщиков с завышенными КП."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.commercial_offer import CommercialOffer
from app.models.lot_supplier import LotSupplier
from app.models.supplier import Supplier
from app.models.tender import Tender


def _tender():
    return Tender(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_tender_id='test',
        title='Тестовый тендер',
        description='Описание',
        status='CP_FULLY_RECEIVED',
    )


def _lot(tender_id):
    return LotSupplier(id=uuid.uuid4(), tender_id=tender_id, supplier_id=uuid.uuid4(),
                       status='CP_RECEIVED', source='manual')


def _offer(lot_id, tender_id, cost):
    return CommercialOffer(
        id=uuid.uuid4(), lot_supplier_id=lot_id, tender_id=tender_id,
        status='FULL', coverage=100.0, total_cost_with_all=cost, margin_percent=20.0,
    )


@pytest.mark.asyncio
async def test_discount_requested_for_overpriced_offer():
    """Поставщику с ценой выше порога отправляется запрос скидки."""
    from app.services.negotiation_service import request_discounts

    tender = _tender()
    lot_a, lot_b = _lot(tender.id), _lot(tender.id)
    offer_a, offer_b = _offer(lot_a.id, tender.id, 100000), _offer(lot_b.id, tender.id, 130000)
    supplier_a = Supplier(id=lot_a.supplier_id, name='A', type='distributor',
                          website='https://a.ru', email='a@a.ru', tags=[])
    supplier_b = Supplier(id=lot_b.supplier_id, name='B', type='distributor',
                          website='https://b.ru', email='b@b.ru', tags=[])

    db = AsyncMock()
    db.get = AsyncMock(side_effect=lambda model, pk: tender if model is Tender else (
        supplier_a if pk == lot_a.supplier_id else supplier_b))
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot_a, lot_b]
    offer_a_result = MagicMock()
    offer_a_result.scalar_one_or_none.return_value = offer_a
    offer_b_result = MagicMock()
    offer_b_result.scalar_one_or_none.return_value = offer_b
    # поставщик B: сколько раз уже просили скидку
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    db.execute = AsyncMock(side_effect=[
        lots_result, offer_a_result, offer_b_result, count_result,
    ])
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    with patch('app.services.settings_service.get_section_settings', new_callable=AsyncMock) as mock_settings, \
         patch('app.services.negotiation_service.build_cp_context', new_callable=AsyncMock) as mock_ctx, \
         patch('app.services.tender_status_service.recalculate_tender_status', new_callable=AsyncMock), \
         patch('app.services.negotiation_service.send_email', new_callable=AsyncMock) as mock_send:
        mock_settings.return_value = {
            'price_diff_threshold_percent': 5.0,
            'max_discount_requests_per_supplier': 2,
        }
        mock_ctx.return_value = {'lot_name': tender.title, 'company_signature': ''}
        mock_send.return_value = (True, '<msg>')
        sent = await request_discounts(str(tender.id), db)

    # Скидку просим только у B (130000 против 100000 = +30%)
    assert sent == 1
    mock_send.assert_awaited_once()
    assert mock_send.await_args.kwargs['to_address'] == 'b@b.ru'


@pytest.mark.asyncio
async def test_no_discount_when_prices_are_close():
    """При небольшом разрыве цен торг не начинается."""
    from app.services.negotiation_service import request_discounts

    tender = _tender()
    lot_a, lot_b = _lot(tender.id), _lot(tender.id)
    offer_a, offer_b = _offer(lot_a.id, tender.id, 100000), _offer(lot_b.id, tender.id, 102000)

    supplier_a = Supplier(id=lot_a.supplier_id, name='A', type='distributor',
                          website='https://a.ru', email='a@a.ru', tags=[])
    supplier_b = Supplier(id=lot_b.supplier_id, name='B', type='distributor',
                          website='https://b.ru', email='b@b.ru', tags=[])

    db = AsyncMock()
    db.get = AsyncMock(side_effect=lambda model, pk: tender if model is Tender else (
        supplier_a if pk == lot_a.supplier_id else supplier_b))
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot_a, lot_b]
    offer_a_result = MagicMock()
    offer_a_result.scalar_one_or_none.return_value = offer_a
    offer_b_result = MagicMock()
    offer_b_result.scalar_one_or_none.return_value = offer_b
    db.execute = AsyncMock(side_effect=[lots_result, offer_a_result, offer_b_result])
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    with patch('app.services.settings_service.get_section_settings', new_callable=AsyncMock) as mock_settings, \
         patch('app.services.tender_status_service.recalculate_tender_status', new_callable=AsyncMock), \
         patch('app.services.negotiation_service.build_cp_context', new_callable=AsyncMock) as mock_ctx, \
         patch('app.services.negotiation_service.send_email', new_callable=AsyncMock) as mock_send:
        mock_settings.return_value = {
            'price_diff_threshold_percent': 5.0,
            'max_discount_requests_per_supplier': 2,
        }
        mock_ctx.return_value = {'lot_name': tender.title, 'company_signature': ''}
        sent = await request_discounts(str(tender.id), db)

    assert sent == 0
    mock_send.assert_not_awaited()
