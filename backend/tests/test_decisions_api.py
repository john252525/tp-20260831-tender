import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.models.tender import Tender

@pytest.mark.asyncio
async def test_list_decisions_empty(app_without_auth):
    mock_session = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    list_result = MagicMock()
    list_result.scalars().all.return_value = []
    mock_session.execute.side_effect = [count_result, list_result]

    with patch('app.api.v1.decisions.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/api/v1/decisions')
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['data'] == []

@pytest.mark.asyncio
async def test_approve_decision_not_found(app_without_auth):
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)

    with patch('app.api.v1.decisions.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post(f'/api/v1/decisions/{uuid.uuid4()}/approve', json={})
    assert response.status_code == 404
