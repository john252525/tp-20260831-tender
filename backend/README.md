# Tender Pipeline Backend

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните переменные.
2. Запустите все контейнеры (API, PostgreSQL, Redis, Celery worker и beat):
   ```bash
   docker-compose up -d
   ```
3. Примените миграции:
   ```bash
   docker-compose exec api alembic upgrade head
   ```
4. Создайте первый API-токен через CLI:
   ```bash
   docker-compose exec api python -m app.cli.token_cli create --description "Admin"
   ```
   Полученный токен используйте в заголовке `X-API-Token`.

## Celery

Celery worker и beat запускаются автоматически через docker-compose:
- `worker` — выполняет задачи: обработка тендеров, синхронизация источников, поиск поставщиков, отправка писем, парсинг КП, переговоры.
- `worker-beat` — периодический планировщик (например, приём входящих писем каждые 5 минут).

Чтобы перезапустить или посмотреть логи:
```bash
docker-compose restart worker
 docker-compose logs -f worker
```

## Структура
- `app/api/v1` – роутеры
- `app/models` – модели SQLAlchemy
- `app/services` – бизнес-логика
- `app/core` – конфигурация, БД, middleware
- `app/workers` – Celery-приложение и задачи
- `migrations` – Alembic
- `tests` – pytest

## Тестирование
```bash
pytest
```

## Примечания
- Храните секреты в `.env`, не коммитьте их.
- Для работы с Google Custom Search и LLM API необходимы соответствующие ключи.
- Синхронизация с ГосПлан API и интеграция с S3/MinIO пока в разработке (заглушки).
