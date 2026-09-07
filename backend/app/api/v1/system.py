import time
from contextlib import suppress
from fastapi import APIRouter, Request
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine

router = APIRouter()

@router.get('/health')
async def health(request: Request):
    db_status = 'healthy'
    try:
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
            await conn.execute(text('SELECT 1 FROM api_tokens LIMIT 0'))
            await conn.execute(text('SELECT 1 FROM settings LIMIT 0'))
    except Exception:
        db_status = 'unhealthy'

    redis_status = 'healthy'
    redis_client = request.app.state.redis
    try:
        await redis_client.ping()
    except Exception:
        redis_status = 'unhealthy'

    uptime = int(time.time() - request.app.state.start_time)
    return {
        'success': True,
        'data': {
            'status': 'healthy' if (db_status == 'healthy' and redis_status == 'healthy') else 'degraded',
            'version': '1.0.0',
            'uptime_seconds': uptime,
            'components': {
                'database': db_status,
                'redis': redis_status,
                'llm_api': 'unknown',
                'tender_source_api': 'unknown'
            }
        }
    }
