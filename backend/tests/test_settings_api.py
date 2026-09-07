import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.models.setting import Setting

@pytest.mark.asyncio
async def test_get_all_settings_success(app_without_auth):
    settings_objs = [
        Setting(section='scoring', key='min_total_score', value=60),
        Setting(section='company', key='legal_name', value='ООО')
    ]
    mock_session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars().all.return_value = settings_objs
    mock_session.execute = AsyncMock(return_value=result_mock)

    with patch('app.api.v1.settings.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/api/v1/settings')
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['data']['scoring']['min_total_score'] == 60

@pytest.mark.asyncio
async def test_get_section_not_found(app_without_auth):
    mock_session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars().all.return_value = []
    mock_session.execute = AsyncMock(return_value=result_mock)

    with patch('app.api.v1.settings.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        with patch('app.services.settings_service.get_section_settings', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = None
            transport = ASGITransport(app=app_without_auth)
            async with AsyncClient(transport=transport, base_url='http://test') as client:
                response = await client.get('/api/v1/settings/scoring')
    assert response.status_code == 404
    data = response.json()
    assert data['error']['code'] == 'NOT_FOUND'

@pytest.mark.asyncio
async def test_get_section_invalid_enum(app_without_auth):
    transport = ASGITransport(app=app_without_auth)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.get('/api/v1/settings/invalid_section')
    assert response.status_code == 422
    data = response.json()
    assert data['error']['code'] == 'VALIDATION_ERROR'
