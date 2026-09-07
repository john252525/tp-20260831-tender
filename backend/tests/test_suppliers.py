import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
from httpx import AsyncClient, ASGITransport
from app.models.supplier import Supplier
from app.models.lot_supplier import LotSupplier

@pytest.mark.asyncio
async def test_list_suppliers_empty(app_without_auth):
    mock_session = AsyncMock()
    count_mock = MagicMock()
    count_mock.scalar_one.return_value = 0
    list_mock = MagicMock()
    list_mock.scalars().all.return_value = []
    mock_session.execute.side_effect = [count_mock, list_mock]

    with patch('app.api.v1.suppliers.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/api/v1/suppliers')
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['data'] == []
    assert data['meta']['total'] == 0

@pytest.mark.asyncio
async def test_create_supplier_success(app_without_auth):
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    with patch('app.api.v1.suppliers.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post('/api/v1/suppliers', json={
                'name': 'ООО Тест',
                'type': 'distributor',
                'email': 'test@example.com',
                'phone': '+79991234567',
                'inn': '1234567890',
                'tags': ['оргтехника'],
            })
    assert response.status_code == 201
    data = response.json()
    assert data['success'] is True
    assert data['data']['name'] == 'ООО Тест'

@pytest.mark.asyncio
async def test_create_supplier_duplicate(app_without_auth):
    existing_supplier = Supplier(name='ООО Тест', email='test@example.com', inn='1234567890')
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_supplier)))

    with patch('app.api.v1.suppliers.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post('/api/v1/suppliers', json={
                'name': 'ООО Тест',
                'email': 'test@example.com',
            })
    assert response.status_code == 409
    data = response.json()
    assert data['error']['code'] == 'CONFLICT'

@pytest.mark.asyncio
async def test_list_suppliers_by_tags(app_without_auth):
    mock_session = AsyncMock()
    count_mock = MagicMock()
    count_mock.scalar_one.return_value = 1
    supplier = Supplier(
        id=uuid.uuid4(),
        name='ООО Тег',
        type='distributor',
        email='tag@example.com',
        phone='+79990000000',
        inn='1234567890',
        tags=['оргтехника', 'ноутбуки'],
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    list_mock = MagicMock()
    list_mock.scalars().all.return_value = [supplier]
    mock_session.execute.side_effect = [count_mock, list_mock]

    with patch('app.api.v1.suppliers.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/api/v1/suppliers?tags=оргтехника')
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert len(data['data']) == 1
    assert data['data'][0]['name'] == 'ООО Тег'

@pytest.mark.asyncio
async def test_delete_supplier_soft(app_without_auth):
    supplier = Supplier(
        id=uuid.uuid4(),
        name='ООО Удаление',
        type='distributor',
        email='del@example.com',
        inn='1234567890',
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=supplier)
    mock_session.commit = AsyncMock()

    with patch('app.api.v1.suppliers.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.delete(f'/api/v1/suppliers/{supplier.id}')
    assert response.status_code == 200
    data = response.json()
    assert data['data']['is_active'] is False
    assert data['data']['deleted_at'] is not None

@pytest.mark.asyncio
async def test_merge_suppliers_success(app_without_auth):
    primary_id = uuid.uuid4()
    secondary_id = uuid.uuid4()

    primary = Supplier(
        id=primary_id,
        name='Primary',
        total_lots=5,
        successful_deals=2,
        total_volume_rub=1000.0,
        is_active=True
    )
    secondary = Supplier(
        id=secondary_id,
        name='Secondary',
        total_lots=3,
        successful_deals=1,
        total_volume_rub=500.0,
        is_active=True
    )

    lot1 = LotSupplier(id=uuid.uuid4(), tender_id=uuid.uuid4(), supplier_id=secondary_id)
    lot2 = LotSupplier(id=uuid.uuid4(), tender_id=uuid.uuid4(), supplier_id=secondary_id)

    mock_session = AsyncMock()
    # При первом get возвращаем primary, затем secondary
    mock_session.get = AsyncMock(side_effect=[primary, secondary])
    # При запросе лотов возвращаем lot1, lot2
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot1, lot2]
    # При проверке существующего лота у primary возвращаем None
    existing_lot_result = MagicMock()
    existing_lot_result.scalar_one_or_none.return_value = None
    mock_session.execute.side_effect = [lots_result, existing_lot_result, existing_lot_result]
    mock_session.commit = AsyncMock()
    mock_session.delete = MagicMock()

    with patch('app.api.v1.suppliers.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post('/api/v1/suppliers/merge', json={
                'primary_id': str(primary_id),
                'secondary_id': str(secondary_id)
            })
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    # Проверяем, что secondary деактивирован
    assert secondary.is_active is False
    assert secondary.deleted_at is not None
    # Проверяем, что лоты переназначены
    assert lot1.supplier_id == primary_id
    assert lot2.supplier_id == primary_id
    # Проверяем агрегаты primary
    assert primary.total_lots == 8
    assert primary.successful_deals == 3
    assert primary.total_volume_rub == 1500.0

@pytest.mark.asyncio
async def test_merge_suppliers_same_id(app_without_auth):
    supplier_id = uuid.uuid4()
    mock_session = AsyncMock()

    with patch('app.api.v1.suppliers.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post('/api/v1/suppliers/merge', json={
                'primary_id': str(supplier_id),
                'secondary_id': str(supplier_id)
            })
    assert response.status_code == 409
    data = response.json()
    assert data['error']['code'] == 'CONFLICT'
