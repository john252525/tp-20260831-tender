import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.middleware import TokenAuthMiddleware
from app.models.api_token import ApiToken

class FakeAsyncSessionContextManager:
    def __init__(self, session):
        self._session = session
    async def __aenter__(self):
        return self._session
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.mark.asyncio
async def test_token_auth_sets_rate_limit_in_scope():
    token_obj = ApiToken(
        id=uuid.uuid4(),
        token='test-token',
        description='test',
        is_active=True,
        rate_limit_per_minute=123,
        last_used_at=None,
        expires_at=None,
    )

    mock_session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=token_obj)
    mock_session.execute = AsyncMock(return_value=result_mock)
    mock_session.commit = AsyncMock()

    async def mock_session_factory():
        return FakeAsyncSessionContextManager(mock_session)

    with patch('app.core.middleware.AsyncSessionLocal', new=mock_session_factory):
        async def fake_app(scope, receive, send):
            assert scope.get('api_token_rate_limit') == 123
            assert scope.get('api_token_id') == str(token_obj.id)
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'', 'more_body': False})
            return

        middleware = TokenAuthMiddleware(fake_app)
        scope = {
            'type': 'http',
            'path': '/api/v1/test',
            'headers': [(b'x-api-token', b'test-token')],
        }
        receive = AsyncMock()
        send = AsyncMock()
        await middleware(scope, receive, send)
        assert send.await_count == 2
        args, _ = send.call_args_list[0]
        assert args[0]['status'] == 200

@pytest.mark.asyncio
async def test_token_auth_invalid_token_returns_401():
    mock_session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=result_mock)

    async def mock_session_factory():
        return FakeAsyncSessionContextManager(mock_session)

    with patch('app.core.middleware.AsyncSessionLocal', new=mock_session_factory):
        async def fake_app(scope, receive, send):
            raise AssertionError('fake_app should not be called')

        middleware = TokenAuthMiddleware(fake_app)
        scope = {
            'type': 'http',
            'path': '/api/v1/test',
            'headers': [(b'x-api-token', b'invalid-token')],
        }
        receive = AsyncMock()
        send = AsyncMock()
        await middleware(scope, receive, send)
        assert send.await_count == 2
        args, _ = send.call_args_list[0]
        assert args[0]['status'] == 401
        body_call = send.call_args_list[1]
        body_data = body_call[0][0]['body']
        assert b'UNAUTHORIZED' in body_data

@pytest.mark.asyncio
async def test_token_auth_expired_token_returns_401():
    token_obj = ApiToken(
        id=uuid.uuid4(),
        token='expired-token',
        description='expired',
        is_active=True,
        rate_limit_per_minute=60,
        last_used_at=None,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # истёк
    )

    mock_session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=token_obj)
    mock_session.execute = AsyncMock(return_value=result_mock)

    async def mock_session_factory():
        return FakeAsyncSessionContextManager(mock_session)

    with patch('app.core.middleware.AsyncSessionLocal', new=mock_session_factory):
        async def fake_app(scope, receive, send):
            raise AssertionError('fake_app should not be called')

        middleware = TokenAuthMiddleware(fake_app)
        scope = {
            'type': 'http',
            'path': '/api/v1/test',
            'headers': [(b'x-api-token', b'expired-token')],
        }
        receive = AsyncMock()
        send = AsyncMock()
        await middleware(scope, receive, send)
        assert send.await_count == 2
        args, _ = send.call_args_list[0]
        assert args[0]['status'] == 401
