"""Тесты напоминаний поставщикам, не ответившим на запрос КП."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.communication import Communication
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
        status='CP_REQUESTED',
    )


@pytest.mark.asyncio
async def test_reminder_sent_after_configured_delay():
    """Напоминание уходит, когда прошло reminder_after_hours."""
    from app.services.negotiation_service import send_reminders

    tender = _tender()
    lot = LotSupplier(id=uuid.uuid4(), tender_id=tender.id, supplier_id=uuid.uuid4(),
                      status='CP_REQUESTED', source='manual')
    supplier = Supplier(id=lot.supplier_id, name='Поставщик', type='distributor',
                        website='https://x.ru', email='x@x.ru', tags=[])
    request_comm = Communication(
        id=uuid.uuid4(), lot_supplier_id=lot.id, tender_id=tender.id,
        direction='outgoing', channel='email', message_type='cp_request',
        sent_at=datetime.now(timezone.utc) - timedelta(hours=30),
    )

    db = AsyncMock()
    db.get = AsyncMock(side_effect=lambda model, pk: tender if model is Tender else supplier)
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot]
    request_result = MagicMock()
    request_result.scalar_one_or_none.return_value = request_comm
    no_reminder_result = MagicMock()
    no_reminder_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(side_effect=[lots_result, request_result, no_reminder_result])
    db.commit = AsyncMock()
    db.add = MagicMock()

    with patch('app.services.settings_service.get_section_settings', new_callable=AsyncMock) as mock_settings, \
         patch('app.services.negotiation_service.send_email', new_callable=AsyncMock) as mock_send:
        mock_settings.return_value = {'reminder_after_hours': 24, 'response_timeout_hours': 48}
        mock_send.return_value = (True, '<msg-id>')
        sent = await send_reminders(str(tender.id), db)

    assert sent == 1
    mock_send.assert_awaited_once()
    added = [c.args[0] for c in db.add.call_args_list]
    assert any(isinstance(obj, Communication) and obj.message_type == 'reminder' for obj in added)


@pytest.mark.asyncio
async def test_no_reminder_before_delay():
    """До истечения reminder_after_hours напоминание не отправляется."""
    from app.services.negotiation_service import send_reminders

    tender = _tender()
    lot = LotSupplier(id=uuid.uuid4(), tender_id=tender.id, supplier_id=uuid.uuid4(),
                      status='CP_REQUESTED', source='manual')
    supplier = Supplier(id=lot.supplier_id, name='Поставщик', type='distributor',
                        website='https://x.ru', email='x@x.ru', tags=[])
    request_comm = Communication(
        id=uuid.uuid4(), lot_supplier_id=lot.id, tender_id=tender.id,
        direction='outgoing', channel='email', message_type='cp_request',
        sent_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )

    db = AsyncMock()
    db.get = AsyncMock(side_effect=lambda model, pk: tender if model is Tender else supplier)
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot]
    request_result = MagicMock()
    request_result.scalar_one_or_none.return_value = request_comm
    db.execute = AsyncMock(side_effect=[lots_result, request_result])
    db.commit = AsyncMock()
    db.add = MagicMock()

    with patch('app.services.settings_service.get_section_settings', new_callable=AsyncMock) as mock_settings, \
         patch('app.services.negotiation_service.send_email', new_callable=AsyncMock) as mock_send:
        mock_settings.return_value = {'reminder_after_hours': 24, 'response_timeout_hours': 48}
        sent = await send_reminders(str(tender.id), db)

    assert sent == 0
    mock_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_overdue_lot_gets_no_response_status():
    """Просроченный лот помечается NO_RESPONSE, но напоминание всё равно уходит."""
    from app.services.negotiation_service import send_reminders

    tender = _tender()
    lot = LotSupplier(id=uuid.uuid4(), tender_id=tender.id, supplier_id=uuid.uuid4(),
                      status='CP_REQUESTED', source='manual')
    supplier = Supplier(id=lot.supplier_id, name='Поставщик', type='distributor',
                        website='https://x.ru', email='x@x.ru', tags=[])
    request_comm = Communication(
        id=uuid.uuid4(), lot_supplier_id=lot.id, tender_id=tender.id,
        direction='outgoing', channel='email', message_type='cp_request',
        sent_at=datetime.now(timezone.utc) - timedelta(hours=200),
    )

    db = AsyncMock()
    db.get = AsyncMock(side_effect=lambda model, pk: tender if model is Tender else supplier)
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot]
    request_result = MagicMock()
    request_result.scalar_one_or_none.return_value = request_comm
    no_reminder_result = MagicMock()
    no_reminder_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(side_effect=[lots_result, request_result, no_reminder_result])
    db.commit = AsyncMock()
    db.add = MagicMock()

    with patch('app.services.settings_service.get_section_settings', new_callable=AsyncMock) as mock_settings, \
         patch('app.services.negotiation_service.send_email', new_callable=AsyncMock) as mock_send:
        mock_settings.return_value = {'reminder_after_hours': 24, 'response_timeout_hours': 48}
        mock_send.return_value = (True, '<msg-id>')
        sent = await send_reminders(str(tender.id), db)

    assert sent == 1
    assert lot.status == 'NO_RESPONSE'
