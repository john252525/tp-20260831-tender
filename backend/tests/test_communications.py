import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.models.tender import Tender
from app.models.lot_supplier import LotSupplier
from app.models.supplier import Supplier
from app.models.communication import Communication
from app.models.task import Task

@pytest.fixture
def mock_celery_send():
    with patch('app.api.v1.communications.send_communications_task.delay') as mock_delay:
        mock_delay.return_value = MagicMock(id='celery-task-id')
        yield mock_delay

@pytest.mark.asyncio
async def test_request_cp_creates_task_and_calls_celery(app_without_auth, mock_celery_send):
    tender_id = uuid.uuid4()
    lot_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    tender = Tender(
        id=tender_id,
        source_id=uuid.uuid4(),
        source_tender_id='stub',
        title='Тестовый тендер',
        description='',
        status='SCORED',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    lot = LotSupplier(
        id=lot_id,
        tender_id=tender_id,
        supplier_id=supplier_id,
        status='PENDING',
        priority=0,
        source='manual',
    )

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=tender)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    # Настраиваем refresh, чтобы устанавливать id задачи
    async def refresh_side_effect(obj):
        obj.id = uuid.uuid4()
    mock_session.refresh = AsyncMock(side_effect=refresh_side_effect)

    # Результат для select LotSupplier
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot]
    mock_session.execute.return_value = lots_result

    with patch('app.api.v1.communications.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post(f'/api/v1/tenders/{tender_id}/request-cp', json={})

    assert response.status_code == 202
    data = response.json()
    assert data['success'] is True
    assert data['data']['status'] == 'ACCEPTED'
    assert 'task_id' in data['data']
    assert 'check_url' in data['data']

    added_objects = [call.args[0] for call in mock_session.add.call_args_list]
    task_obj = next((obj for obj in added_objects if isinstance(obj, Task)), None)
    assert task_obj is not None
    assert task_obj.task_type == 'SEND_COMMUNICATIONS'
    assert task_obj.status == 'PENDING'

    mock_celery_send.assert_called_once_with(str(task_obj.id))
    assert not any(isinstance(obj, Communication) for obj in added_objects)

@pytest.mark.asyncio
async def test_request_cp_no_suppliers_skips_celery(app_without_auth, mock_celery_send):
    tender_id = uuid.uuid4()
    tender = Tender(
        id=tender_id,
        source_id=uuid.uuid4(),
        source_tender_id='stub',
        title='Тестовый тендер',
        description='',
        status='SCORED',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=tender)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    async def refresh_side_effect(obj):
        obj.id = uuid.uuid4()
    mock_session.refresh = AsyncMock(side_effect=refresh_side_effect)

    lots_result = MagicMock()
    lots_result.scalars().all.return_value = []
    mock_session.execute.return_value = lots_result

    with patch('app.api.v1.communications.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post(f'/api/v1/tenders/{tender_id}/request-cp', json={})

    assert response.status_code == 202
    data = response.json()
    assert data['success'] is True

    added_objects = [call.args[0] for call in mock_session.add.call_args_list]
    task_obj = next((obj for obj in added_objects if isinstance(obj, Task)), None)
    assert task_obj is not None
    assert task_obj.status == 'COMPLETED'
    assert task_obj.result_summary == 'Нет привязанных поставщиков'

    mock_celery_send.assert_not_called()

@pytest.mark.asyncio
async def test_list_communications(app_without_auth):
    tender_id = uuid.uuid4()
    lot_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    tender = Tender(id=tender_id, source_id=uuid.uuid4(), source_tender_id='stub', title='Test', description='', status='SCORED')
    lot = LotSupplier(id=lot_id, tender_id=tender_id, supplier_id=supplier_id, status='PENDING', priority=0, source='manual')
    supplier = Supplier(id=supplier_id, name='ООО Поставщик', type='distributor', email='supplier@example.com')
    comm = Communication(
        id=uuid.uuid4(),
        lot_supplier_id=lot_id,
        tender_id=tender_id,
        direction='outgoing',
        channel='email',
        subject='Запрос',
        body_text='Текст',
        message_type='cp_request',
        sent_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(side_effect=[tender, supplier])
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot]
    comms_result = MagicMock()
    comms_result.scalars().all.return_value = [comm]
    mock_session.execute.side_effect = [lots_result, comms_result]

    with patch('app.api.v1.communications.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get(f'/api/v1/tenders/{tender_id}/communications')

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert len(data['data']['supplier_threads']) == 1
    assert len(data['data']['supplier_threads'][0]['messages']) == 1

@pytest.mark.asyncio
async def test_send_message_success(app_without_auth):
    tender_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    lot = LotSupplier(id=uuid.uuid4(), tender_id=tender_id, supplier_id=supplier_id, status='PENDING', priority=0, source='manual')
    tender = Tender(id=tender_id, source_id=uuid.uuid4(), source_tender_id='stub', title='Test', description='', status='SCORED')

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=tender)
    lot_result = MagicMock()
    lot_result.scalar_one_or_none.return_value = lot
    mock_session.execute.return_value = lot_result
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    with patch('app.api.v1.communications.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post(f'/api/v1/tenders/{tender_id}/communications/send', json={
                'supplier_id': str(supplier_id),
                'channel': 'email',
                'subject': 'Test subject',
                'body': 'Test body',
                'message_type': 'manual'
            })

    assert response.status_code == 201
    data = response.json()
    assert data['success'] is True
    assert 'id' in data['data']
    assert data['data']['sent_at'] is not None
