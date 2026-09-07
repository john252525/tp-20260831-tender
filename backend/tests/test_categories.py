import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.models.category import Category
from app.models.task import Task

@pytest.mark.asyncio
async def test_create_category_success(app_without_auth):
    mock_session = AsyncMock()
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = existing_result
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)

    with patch('app.api.v1.categories.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        with patch('app.api.v1.categories.generate_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.0]*1536
            transport = ASGITransport(app=app_without_auth)
            async with AsyncClient(transport=transport, base_url='http://test') as client:
                response = await client.post('/api/v1/categories', json={
                    'name': 'Оргтехника',
                    'description': 'Компьютеры, ноутбуки',
                    'keywords': ['ПК', 'ноутбук']
                })
    assert response.status_code == 201
    data = response.json()
    assert data['success'] is True
    assert data['data']['name'] == 'Оргтехника'
    assert data['data']['embedding_status'] == 'generated'

@pytest.mark.asyncio
async def test_create_category_duplicate(app_without_auth):
    mock_session = AsyncMock()
    existing_result = MagicMock()
    existing_category = Category(name='Test', description='desc', keywords=[])
    existing_result.scalar_one_or_none.return_value = existing_category
    mock_session.execute.return_value = existing_result
    mock_session.get = AsyncMock(return_value=None)

    with patch('app.api.v1.categories.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post('/api/v1/categories', json={
                'name': 'Test',
                'description': 'desc',
                'keywords': []
            })
    assert response.status_code == 409
    data = response.json()
    assert data['error']['code'] == 'CONFLICT'

@pytest.mark.asyncio
async def test_delete_category_soft(app_without_auth):
    category = Category(id=uuid.uuid4(), name='Test', description='desc', keywords=[], is_active=True)
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=category)
    mock_session.commit = AsyncMock()

    with patch('app.api.v1.categories.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.delete(f'/api/v1/categories/{category.id}')
    assert response.status_code == 200
    data = response.json()
    assert data['data']['is_active'] is False

@pytest.mark.asyncio
async def test_patch_category(app_without_auth):
    category = Category(id=uuid.uuid4(), name='Test', description='desc', keywords=[], is_active=True)
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=category)
    mock_session.commit = AsyncMock()
    mock_session.execute = AsyncMock()

    with patch('app.api.v1.categories.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        with patch('app.api.v1.categories.generate_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.0]*1536
            transport = ASGITransport(app=app_without_auth)
            async with AsyncClient(transport=transport, base_url='http://test') as client:
                response = await client.patch(f'/api/v1/categories/{category.id}', json={
                    'description': 'Новое описание'
                })
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_bulk_import_creates_categories_and_task(app_without_auth):
    mock_session = AsyncMock()
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = existing_result
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)

    with patch('app.api.v1.categories.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        with patch('app.api.v1.categories.generate_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.0]*1536
            transport = ASGITransport(app=app_without_auth)
            async with AsyncClient(transport=transport, base_url='http://test') as client:
                response = await client.post('/api/v1/categories/bulk-import', json={
                    'categories': [
                        {'name': 'Оргтехника', 'description': 'Компьютеры', 'keywords': ['ПК']},
                        {'name': 'Канцелярия', 'description': 'Бумага', 'keywords': ['бумага']}
                    ]
                })
    assert response.status_code == 202
    data = response.json()
    assert data['success'] is True
    assert 'task_id' in data['data']
    assert data['data']['status'] == 'ACCEPTED'
    assert 'check_url' in data['data']
    # Проверяем, что добавлены две категории и одна задача
    added_objects = [call.args[0] for call in mock_session.add.call_args_list]
    categories_added = [obj for obj in added_objects if isinstance(obj, Category)]
    tasks_added = [obj for obj in added_objects if isinstance(obj, Task)]
    assert len(categories_added) == 2
    assert len(tasks_added) == 1
    # Проверяем, что задача сохранена со статусом COMPLETED
    task = tasks_added[0]
    assert task.status == 'COMPLETED'
    assert task.progress_percent == 100.0
    assert task.result_summary is not None

@pytest.mark.asyncio
async def test_search_categories(app_without_auth):
    mock_session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars().all.return_value = []
    count_mock = MagicMock()
    count_mock.scalar_one.return_value = 0
    mock_session.execute.side_effect = [count_mock, result_mock]

    with patch('app.api.v1.categories.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/api/v1/categories?search=ноутбук')
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['data'] == []
    assert data['meta']['total'] == 0
