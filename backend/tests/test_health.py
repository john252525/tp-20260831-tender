import pytest
import time
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture(autouse=True)
def set_start_time(monkeypatch):
    monkeypatch.setattr(app.state, 'start_time', time.time())

@pytest.mark.asyncio
async def test_health_without_token(monkeypatch):
    with patch('app.api.v1.system.engine.connect') as mock_engine_connect:
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        mock_conn_context = AsyncMock()
        mock_conn_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn_context.__aexit__ = AsyncMock(return_value=None)
        mock_engine_connect.return_value = mock_conn_context

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        monkeypatch.setattr(app.state, 'redis', mock_redis)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/api/v1/health')
    assert response.status_code == 200
    data = response.json()
    assert data['data']['components']['database'] == 'healthy'
    assert data['data']['components']['redis'] == 'healthy'
    assert data['data']['status'] == 'healthy'

@pytest.mark.asyncio
async def test_health_db_failure(monkeypatch):
    with patch('app.api.v1.system.engine.connect', side_effect=Exception('DB unavailable')):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        monkeypatch.setattr(app.state, 'redis', mock_redis)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/api/v1/health')
    assert response.status_code == 200
    data = response.json()
    assert data['data']['components']['database'] == 'unhealthy'
    assert data['data']['status'] == 'degraded'

@pytest.mark.asyncio
async def test_health_redis_failure(monkeypatch):
    with patch('app.api.v1.system.engine.connect') as mock_engine_connect:
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        mock_conn_context = AsyncMock()
        mock_conn_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn_context.__aexit__ = AsyncMock(return_value=None)
        mock_engine_connect.return_value = mock_conn_context

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception('Redis unavailable'))
        monkeypatch.setattr(app.state, 'redis', mock_redis)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/api/v1/health')
    assert response.status_code == 200
    data = response.json()
    assert data['data']['components']['redis'] == 'unhealthy'
    assert data['data']['status'] == 'degraded'

@pytest.mark.asyncio
async def test_metrics_without_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.get('/api/v1/metrics')
    assert response.status_code == 200
    assert 'text/plain' in response.headers['content-type']
