import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import text
from httpx import Response
from app.models.tender import Tender
from app.models.tender_position import TenderPosition
from app.models.category import Category
from app.models.supplier import Supplier
from app.services.supplier_search import (
    search_suppliers_for_tender,
    _extract_domain,
    _deduplicate,
    _search_external,
    _search_internal,
)

@pytest.mark.asyncio
async def test_search_suppliers_internal_only():
    tender = Tender(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_tender_id='test',
        title='Поставка ноутбуков',
        description='',
        nmck=1000000.0,
        status='SCORED',
        matched_category_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    category = Category(
        id=tender.matched_category_id,
        name='Оргтехника',
        description='Компьютеры',
        keywords=['ноутбук'],
        is_active=True,
    )
    supplier = Supplier(
        id=uuid.uuid4(),
        name='ООО Техно',
        type='distributor',
        tags=['ноутбуки', 'оргтехника'],
        is_active=True,
    )

    mock_db = AsyncMock()
    # Настраиваем get: first call returns tender, second returns category
    mock_db.get = AsyncMock(side_effect=[tender, category])
    positions_result = MagicMock()
    positions_result.scalars().all.return_value = []
    suppliers_result = MagicMock()
    suppliers_result.scalars().all.return_value = [supplier]
    mock_db.execute.side_effect = [positions_result, suppliers_result]

    with patch('app.services.supplier_search._search_external', new_callable=AsyncMock) as mock_google:
        mock_google.return_value = []
        result = await search_suppliers_for_tender(
            tender_id=tender.id,
            max_suppliers=10,
            channels=['internal_db'],
            priority_order=['manufacturer', 'distributor', 'wholesaler'],
            db=mock_db
        )
    assert result['total_found'] == 1
    assert result['results'][0]['name'] == 'ООО Техно'
    assert result['results'][0]['already_in_db'] is True

@pytest.mark.asyncio
async def test_search_external_parses_results():
    """Внешний поиск отдаёт кандидатов с доменом и осмысленным именем."""
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'success': True,
        'results': [
            # SEO-заголовок не должен становиться именем поставщика
            {'url': 'https://perchatki21.ru/catalog', 'title': '  купить в СПб - цена на ...'},
            # маркетплейс не является поставщиком
            {'url': 'https://www.avito.ru/items', 'title': 'Объявления'},
        ],
    }
    mock_response.raise_for_status = MagicMock()
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        results = await _search_external(['нитриловые перчатки оптом'])

    assert len(results) == 1
    assert results[0]['source'] == 'google'
    assert results[0]['domain'] == 'perchatki21.ru'
    # Имя взято из домена, а не из SEO-заголовка
    assert results[0]['name'] == 'Perchatki21'

@pytest.mark.asyncio
async def test_extract_domain():
    assert _extract_domain('https://www.example.com/page') == 'example.com'
    assert _extract_domain('http://sub.domain.co.uk/path') == 'co.uk'
    assert _extract_domain('') == ''

def test_deduplicate_by_domain():
    candidates = [
        {'name': 'A', 'domain': 'example.com', 'email': '', 'inn': '', 'phone': ''},
        {'name': 'B', 'domain': 'example.com', 'email': '', 'inn': '', 'phone': ''},
        {'name': 'C', 'domain': 'other.com', 'email': '', 'inn': '', 'phone': ''},
    ]
    unique = _deduplicate(candidates)
    assert len(unique) == 2
    assert any(c['name'] == 'A' for c in unique)
    assert any(c['name'] == 'C' for c in unique)
