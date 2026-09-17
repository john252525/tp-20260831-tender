# CONVENTIONS

Кодстайл, соглашения, паттерны. Чтобы не переизобретать.

## Backend

- Python 3.12, async везде (SQLAlchemy 2.0 async, httpx.AsyncClient)
- Форматирование: одинарные кавычки, отступ 4, длина строки около 100
- Логирование: structlog, события в формате domain.action,
  например tender_sync.completed, cp_parser.llm_error
- Секреты и настройки: из app.core.config.settings (pydantic-settings)
- Настройки, изменяемые в рантайме: из БД через settings_service.get_section_settings
- Ошибки: доменные через AppException (NotFoundError, ConflictError),
  внешние оборачиваются в try с логированием warning

## Работа с БД

- Сессии: AsyncSessionLocal из app.core.database, в API через Depends(get_db)
- Операции, изменяющие данные: commit в конце, flush для промежуточных id
- Идемпотентность: удалять и вставлять заново (delete + insert) для позиций,
  документов, требований при переобработке
- Индексы: имена вида idx_<таблица>_<поле>
- Миграции: alembic, файлы вида NNN_описание.py

## Celery

- Задачи: декоратор @celery_app.task, внутри async def _run() и asyncio.run
- Сессия: своя AsyncSessionLocal на задачу, в конце await engine.dispose()
- Прогресс: через _update_task или pipeline_progress
- Идемпотентность: перед постановкой проверять активные задачи по entity_id
- Новые задачи регистрировать в TASK_RUNNERS (для перезапуска зависших)

## Тесты

- pytest + pytest-asyncio, маркер @pytest.mark.asyncio
- Изоляция: моки через AsyncMock и MagicMock, реальная БД не используется
- Файлы: tests/test_<модуль>.py
- Запуск: docker compose exec -T backend python -m pytest tests/<файл> -q -p no:cacheprovider
- Для db.execute с несколькими вызовами: side_effect со списком результатов

## Frontend

- React 18, TypeScript, функциональные компоненты
- Данные: TanStack Query (useQuery, useMutation), не useEffect для загрузки
- API: из frontend/src/api/*.ts, обёртка apiClient (axios)
- Токен: localStorage api_token, заголовок X-Api-Token
- Стили: Tailwind, утилита cn для условных классов
- Тесты: jest + jsdom, Testing Library, jest.mock для сетевого слоя

## Деплой

- Бинд-маунтов нет: правки требуют docker compose build и up -d --no-deps
- docker compose cp годится только для быстрой отладки
- После смены celery_app.py перезапускать и worker-beat
- Переменные окружения: .env, перезапуск обязателен
