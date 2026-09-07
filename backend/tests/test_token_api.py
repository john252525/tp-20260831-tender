import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_create_token_success(app_without_auth):
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.execute = AsyncMock()

    with patch('app.api.v1.tokens.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post('/api/v1/tokens', json={
                'description': 'Test token',
                'rate_limit_per_minute': 60,
                'expires_in_days': None
            })
    assert response.status_code == 201
    data = response.json()
    assert data['success'] is True
    assert 'token' in data['data']
    assert data['data']['description'] == 'Test token'

@pytest.mark.asyncio
async def test_list_tokens_success(app_without_auth):
    from app.models.api_token import ApiToken
    token_obj = ApiToken(
        id=__import__('uuid').uuid4(),
        token='test-token-full-string',
        description='Test',
        is_active=True,
        rate_limit_per_minute=60,
        last_used_at=None,
        expires_at=None,
        created_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc),
        updated_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc),
    )
    mock_session = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    list_result = MagicMock()
    list_result.scalars().all.return_value = [token_obj]
    mock_session.execute.side_effect = [count_result, list_result]

    with patch('app.api.v1.tokens.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/api/v1/tokens')
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert len(data['data']) == 1
    assert data['data'][0]['token_preview'] is not None
