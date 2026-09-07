import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.models.task import Task

@pytest.mark.asyncio
async def test_get_task_status_success(app_without_auth):
    task = Task(
        id=uuid.uuid4(),
        celery_task_id=None,
        task_type='PROCESS_TENDER',
        status='COMPLETED',
        progress_percent=100.0,
        entity_type=None,
        entity_id=None,
        result_summary='Выполнено',
        error_message=None,
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=task)

    with patch('app.api.v1.tasks.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get(f'/api/v1/tasks/{task.id}')
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['data']['id'] == str(task.id)
    assert data['data']['status'] == 'COMPLETED'
    assert data['data']['progress_percent'] == 100.0

@pytest.mark.asyncio
async def test_get_task_not_found(app_without_auth):
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)

    with patch('app.api.v1.tasks.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get(f'/api/v1/tasks/{uuid.uuid4()}')
    assert response.status_code == 404
    data = response.json()
    assert data['error']['code'] == 'NOT_FOUND'

@pytest.mark.asyncio
async def test_list_tasks_empty(app_without_auth):
    mock_session = AsyncMock()
    count_mock = MagicMock()
    count_mock.scalar_one.return_value = 0
    list_mock = MagicMock()
    list_mock.scalars().all.return_value = []
    mock_session.execute.side_effect = [count_mock, list_mock]

    with patch('app.api.v1.tasks.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/api/v1/tasks')
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['data'] == []
    assert data['meta']['total'] == 0
