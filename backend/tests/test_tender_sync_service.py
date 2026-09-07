import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tender_source import TenderSource
from app.models.tender import Tender
from app.services.tender_sync_service import sync_tenders_from_source

@pytest.mark.asyncio
async def test_sync_from_gosplan():
    source_id = uuid.uuid4()
    source = TenderSource(
        id=source_id,
        name='ГосПлан',
        type='aggregator_api',
        api_url='https://v2.gosplan.info',
        api_key_encrypted='',
        config={'page_size': 10},
        is_active=True,
        last_sync_at=None,
        last_sync_status=None,
        last_error=None,
    )

    purchase = {
        'purchase_number': '1234567890',
        'object_info': 'Поставка ноутбуков',
        'max_price': 1000000.0,
        'published_at': (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        'collecting_finished_at': (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
        'responsible': '7712345678',
        'customers': ['7712345678'],
    }

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=source)

    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = existing_result

    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    with patch('app.services.tender_sync_service.GosPlanClient') as MockClient:
        mock_client = AsyncMock()
        mock_client.search_purchases = AsyncMock(return_value=[purchase])
        MockClient.return_value = mock_client

        created = await sync_tenders_from_source(source_id, mock_db)

    assert len(created) == 1
    assert source.last_sync_status == 'success'
    assert source.last_sync_at is not None

    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    tender = next((obj for obj in added_objects if isinstance(obj, Tender)), None)
    assert tender is not None
    assert tender.source_tender_id == '1234567890'
    assert tender.title == 'Поставка ноутбуков'
    assert tender.customer_inn == '7712345678'
    assert tender.published_at is not None
    assert tender.deadline_at is not None
    assert tender.source_url.endswith('1234567890')

    # Проверяем, что search_purchases вызван с skip=0
    mock_client.search_purchases.assert_called_once()
    call_kwargs = mock_client.search_purchases.call_args[1]
    assert call_kwargs['skip'] == 0
    assert call_kwargs['limit'] == 10

@pytest.mark.asyncio
async def test_sync_pagination():
    source_id = uuid.uuid4()
    source = TenderSource(
        id=source_id,
        name='ГосПлан',
        type='aggregator_api',
        api_url='https://v2.gosplan.info',
        api_key_encrypted='',
        config={'page_size': 2, 'max_pages': 10},
        is_active=True,
        last_sync_at=None,
        last_sync_status=None,
        last_error=None,
    )

    purchase1 = {'purchase_number': '1', 'object_info': 'Тендер 1'}
    purchase2 = {'purchase_number': '2', 'object_info': 'Тендер 2'}
    purchase3 = {'purchase_number': '3', 'object_info': 'Тендер 3'}

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=source)
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = existing_result
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    with patch('app.services.tender_sync_service.GosPlanClient') as MockClient:
        mock_client = AsyncMock()
        # Первый вызов возвращает 2 записи, второй - 1 запись, третий не должен вызываться
        mock_client.search_purchases = AsyncMock(side_effect=[[purchase1, purchase2], [purchase3]])
        MockClient.return_value = mock_client

        created = await sync_tenders_from_source(source_id, mock_db)

    assert len(created) == 3
    assert mock_client.search_purchases.call_count == 2
    # Проверяем skip для каждого вызова
    first_call_kwargs = mock_client.search_purchases.call_args_list[0][1]
    second_call_kwargs = mock_client.search_purchases.call_args_list[1][1]
    assert first_call_kwargs['skip'] == 0
    assert second_call_kwargs['skip'] == 2

    added_tenders = [call.args[0] for call in mock_db.add.call_args_list if isinstance(call.args[0], Tender)]
    assert {t.source_tender_id for t in added_tenders} == {'1', '2', '3'}

@pytest.mark.asyncio
async def test_sync_stub_fallback():
    source_id = uuid.uuid4()
    source = TenderSource(
        id=source_id,
        name='Другой источник',
        type='direct_api',
        api_url='https://example.com',
        api_key_encrypted='',
        config={},
        is_active=True,
        last_sync_at=None,
        last_sync_status=None,
        last_error=None,
    )

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=source)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    created = await sync_tenders_from_source(source_id, mock_db)

    assert len(created) == 10
    assert source.last_sync_status == 'success'
    assert all(isinstance(t, Tender) for t in created)

@pytest.mark.asyncio
async def test_sync_gosplan_error():
    source_id = uuid.uuid4()
    source = TenderSource(
        id=source_id,
        name='ГосПлан',
        type='aggregator_api',
        api_url='https://v2.gosplan.info',
        api_key_encrypted='',
        config={},
        is_active=True,
        last_sync_at=None,
        last_sync_status=None,
        last_error=None,
    )

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=source)
    mock_db.commit = AsyncMock()

    with patch('app.services.tender_sync_service.GosPlanClient') as MockClient:
        mock_client = AsyncMock()
        mock_client.search_purchases = AsyncMock(side_effect=Exception('API error'))
        MockClient.return_value = mock_client

        with pytest.raises(Exception):
            await sync_tenders_from_source(source_id, mock_db)

    assert source.last_sync_status == 'error'
    assert source.last_error == 'API error'
    assert source.last_sync_at is not None  # last_sync_at должен обновляться при ошибке
