from contextlib import asynccontextmanager
import time
import redis.asyncio as redis
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging_config import setup_logging
from app.core.middleware import TokenAuthMiddleware, RateLimitMiddleware

setup_logging()
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.start_time = time.time()
    # Создаём Redis-клиент и сохраняем в app.state
    app.state.redis = redis.from_url(settings.redis_url)
    yield
    # Закрываем Redis при остановке приложения
    await app.state.redis.aclose()

app = FastAPI(
    title='Тендерный конвейер API',
    version='1.0.0',
    docs_url='/docs',
    redoc_url='/redoc',
    openapi_url='/openapi.json',
    lifespan=lifespan
)

# CORS настройки
allow_origins = settings.cors_origins
allow_credentials = False if allow_origins == ['*'] else True
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Правильный порядок: сначала добавляем RateLimitMiddleware (он станет внутренним),
# затем TokenAuthMiddleware (станет внешним и выполнится первым).
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TokenAuthMiddleware)

app.include_router(api_router, prefix='/api/v1')

# Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint='/api/v1/metrics')

# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'success': False,
            'error': {
                'code': exc.code,
                'message': exc.message,
                'details': exc.details or None
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            'success': False,
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': 'Ошибка валидации данных',
                'details': exc.errors()
            }
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'success': False,
            'error': {
                'code': 'HTTP_ERROR',
                'message': str(exc.detail)
            }
        }
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception('error.unhandled')
    return JSONResponse(
        status_code=500,
        content={
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Внутренняя ошибка сервера'
            }
        }
    )
