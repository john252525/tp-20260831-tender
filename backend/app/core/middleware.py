import time
from datetime import datetime, timezone
import structlog
from starlette.responses import JSONResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.api_token import ApiToken

logger = structlog.get_logger()

class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        path = scope.get('path', '')
        if path in settings.auth_exempt_paths:
            await self.app(scope, receive, send)
            return

        token = None
        for name, value in scope['headers']:
            if name == b'x-api-token':
                token = value.decode()
                break

        if not token:
            response = self._error_response(401, 'UNAUTHORIZED', 'Invalid or expired API token')
            await response(scope, receive, send)
            return

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ApiToken).where(ApiToken.token == token))
            api_token = result.scalar_one_or_none()

            if not api_token or not api_token.is_active:
                response = self._error_response(401, 'UNAUTHORIZED', 'Invalid or expired API token')
                await response(scope, receive, send)
                return

            now = datetime.now(timezone.utc)
            if api_token.expires_at and api_token.expires_at < now:
                response = self._error_response(401, 'UNAUTHORIZED', 'Invalid or expired API token')
                await response(scope, receive, send)
                return

            if api_token.last_used_at is None or (now - api_token.last_used_at).total_seconds() > 60:
                api_token.last_used_at = now
                await session.commit()

            try:
                structlog.contextvars.bind_contextvars(api_token_id=str(api_token.id))
                logger.info('api_token.request', path=path)
            finally:
                structlog.contextvars.unbind_contextvars('api_token_id')

            scope['api_token_id'] = str(api_token.id)
            scope['api_token_rate_limit'] = api_token.rate_limit_per_minute

        await self.app(scope, receive, send)

    def _error_response(self, status_code, code, message):
        content = {'success': False, 'error': {'code': code, 'message': message}}
        return JSONResponse(content, status_code=status_code)

class RateLimitMiddleware:
    """Rate limiting middleware, использующий Redis для хранения счётчиков."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        path = scope.get('path', '')
        if path in settings.auth_exempt_paths:
            await self.app(scope, receive, send)
            return

        token = None
        for name, value in scope['headers']:
            if name == b'x-api-token':
                token = value.decode()
                break

        if not token:
            await self.app(scope, receive, send)
            return

        rate_limit = scope.get('api_token_rate_limit', 60)

        # Получаем Redis-клиент из корневого app.state (scope.app), не из self.app
        root_app = scope.get('app')
        redis_client = getattr(getattr(root_app, 'state', None), 'redis', None)
        if redis_client is None:
            # Если Redis недоступен, пропускаем лимит (или можно вернуть ошибку)
            await self.app(scope, receive, send)
            return

        key = f'rate_limit:{token}'
        try:
            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, 60)
            if current > rate_limit:
                response = self._error_response(429, 'RATE_LIMITED', 'Rate limit exceeded')
                await response(scope, receive, send)
                return
        except Exception as exc:
            logger.error('rate_limit.redis_error', error=str(exc))
            # При ошибке Redis пропускаем запрос

        await self.app(scope, receive, send)

    def _error_response(self, status_code, code, message):
        content = {'success': False, 'error': {'code': code, 'message': message}}
        return JSONResponse(content, status_code=status_code)
