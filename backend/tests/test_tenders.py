import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.models.tender import Tender
from app.models.tender_source import TenderSource
from app.models.tender_status_history import TenderStatusHistory
from app.models.task import Task

@pytest.fixture
def mock_celery_process():
    with patch('app.api.v1.tenders.process_tender_task.delay') as mock_delay:
        mock_delay.return_value = MagicMock(id='celery-task-id')
        yield mock_delay

@pytest.mark.asyncio
async def test_create_tender_auto_processing_sets_celery(app_without_auth, mock_celery_process):
    manual_source_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    source = TenderSource(id=manual_source_id, name='Manual', type='direct_api', api_url='https://manual.local', api_key_encrypted='', config={}, is_active=True,
                          created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=source)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    with patch('app.api.v1.tenders.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post('/api/v1/tenders', json={
                'title': 'Тестовый тендер',
                'description': '',
                'nmck': 100000.0,
                'skip_auto_processing': False
            })

    assert response.status_code == 201
    data = response.json()
    assert data['success'] is True
    assert 'task_id' in data['data']

    added_objects = [call.args[0] for call in mock_session.add.call_args_list]
    task_obj = next((obj for obj in added_objects if isinstance(obj, Task)), None)
    assert task_obj is not None
    assert task_obj.task_type == 'PROCESS_TENDER'
    mock_celery_process.assert_called_once_with(str(task_obj.id))

@pytest.mark.asyncio
async def test_reprocess_tender_sets_celery(app_without_auth, mock_celery_process):
    tender_id = uuid.uuid4()
    tender = Tender(id=tender_id, source_id=uuid.uuid4(), source_tender_id='stub', title='Test', description='', status='NEW',
                    created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=tender)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    with patch('app.api.v1.tenders.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post(f'/api/v1/tenders/{tender_id}/reprocess', json={'from_stage': 'SCORING'})

    assert response.status_code == 202
    added_objects = [call.args[0] for call in mock_session.add.call_args_list]
    task_obj = next((obj for obj in added_objects if isinstance(obj, Task)), None)
    assert task_obj is not None
    mock_celery_process.assert_called_once_with(str(task_obj.id))

@pytest.mark.asyncio
async def test_search_suppliers_sets_celery(app_without_auth):
    tender_id = uuid.uuid4()
    tender = Tender(id=tender_id, source_id=uuid.uuid4(), source_tender_id='stub', title='Test', description='', status='SCORED')
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=tender)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    with patch('app.api.v1.tenders.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        with patch('app.api.v1.tenders.search_suppliers_task.delay') as mock_delay:
            mock_delay.return_value = MagicMock(id='celery-id')
            transport = ASGITransport(app=app_without_auth)
            async with AsyncClient(transport=transport, base_url='http://test') as client:
                response = await client.post(f'/api/v1/tenders/{tender_id}/search-suppliers', json={})

    assert response.status_code == 202
    added_objects = [call.args[0] for call in mock_session.add.call_args_list]
    task_obj = next((obj for obj in added_objects if isinstance(obj, Task)), None)
    assert task_obj is not None
    mock_delay.assert_called_once_with(str(task_obj.id))

@pytest.mark.asyncio
async def test_get_tender_not_found(app_without_auth):
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)
    with patch('app.api.v1.tenders.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get(f'/api/v1/tenders/{uuid.uuid4()}')
    assert response.status_code == 404
