import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.v1.router import api_router
from app.core.exceptions import AppException

@pytest.fixture
def app_without_auth():
    app = FastAPI()
    app.include_router(api_router, prefix='/api/v1')
    # Добавляем обработчики ошибок для корректной выдачи
    @app.exception_handler(AppException)
    async def app_exception_handler(request, exc: AppException):
        from fastapi.responses import JSONResponse
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
    async def validation_exception_handler(request, exc: RequestValidationError):
        from fastapi.responses import JSONResponse
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
    async def http_exception_handler(request, exc: StarletteHTTPException):
        from fastapi.responses import JSONResponse
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
    return app
