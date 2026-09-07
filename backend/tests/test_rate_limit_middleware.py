import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.core.middleware import RateLimitMiddleware

class DummyApp:
    """Фейковое ASGI-приложение с состоянием Redis."""
    def __init__(self, redis_client):
        self.state = SimpleNamespace(redis=redis_client)

    async def __call__(self, scope, receive, send):
        await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'', 'more_body': False})

@pytest.fixture
def redis_mock():
    """Фейковый Redis с счётчиком: первый incr возвращает 1, второй — 2."""
    redis = AsyncMock()
    redis.incr = AsyncMock(side_effect=[1, 2])
    redis.expire = AsyncMock()
    return redis

@pytest.mark.asyncio
async def test_rate_limit_uses_personal_limit_from_scope(redis_mock):
    app = DummyApp(redis_mock)
    middleware = RateLimitMiddleware(app)

    # Первый запрос с лимитом 1 должен пройти
    scope1 = {
        'type': 'http',
        'path': '/api/v1/test',
        'headers': [(b'x-api-token', b'rate-limited-token')],
        'api_token_rate_limit': 1,
    }
    send1 = AsyncMock()
    await middleware(scope1, AsyncMock(), send1)
    # Первый запрос должен отправить 200 (start + body)
    assert send1.await_count == 2
    first_call_args = send1.call_args_list[0][0][0]
    assert first_call_args['status'] == 200

    # Redis.incr был вызван один раз, expire установлен на 60
    redis_mock.incr.assert_awaited_once()
    redis_mock.expire.assert_awaited_once_with('rate_limit:rate-limited-token', 60)

    # Второй запрос с тем же токеном, лимит 1, должен вернуть 429
    scope2 = {
        'type': 'http',
        'path': '/api/v1/test',
        'headers': [(b'x-api-token', b'rate-limited-token')],
        'api_token_rate_limit': 1,
    }
    send2 = AsyncMock()
    await middleware(scope2, AsyncMock(), send2)
    # Ответ 429 состоит из start + body, поэтому await_count == 2
    assert send2.await_count == 2
    second_first_call_args = send2.call_args_list[0][0][0]
    assert second_first_call_args['status'] == 429

    # incr вызван второй раз, expire не вызывался повторно (только при current == 1)
    assert redis_mock.incr.await_count == 2
    redis_mock.expire.assert_awaited_once()

@pytest.mark.asyncio
async def test_rate_limit_no_redis_proceeds():
    app = DummyApp(None)
    middleware = RateLimitMiddleware(app)

    scope = {
        'type': 'http',
        'path': '/api/v1/test',
        'headers': [(b'x-api-token', b'some-token')],
        'api_token_rate_limit': 1,
    }
    send = AsyncMock()
    await middleware(scope, AsyncMock(), send)
    # Запрос должен пройти без ограничения
    assert send.await_count == 2
    first_call_args = send.call_args_list[0][0][0]
    assert first_call_args['status'] == 200
