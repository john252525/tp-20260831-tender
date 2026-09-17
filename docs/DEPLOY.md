# Деплой тендерного проекта

## Быстрый путь

    git clone git@github.com:john252525/tp-20260831-tender-deploy.git
    cd tp-20260831-tender-deploy
    ./scripts/deploy.sh

Скрипт сам проверит окружение, создаст `.env` со сгенерированными секретами,
соберёт образы, поднимет сервисы, дождётся готовности и создаст первый API-токен.

Дальше нужно вручную заполнить в `.env`: `LLM_API_KEY`, `SMTP_*`, `IMAP_*`,
`EMBEDDING_SERVICE_URL` — и запустить `./scripts/deploy.sh` повторно
(он идемпотентен).

## Что делает scripts/deploy.sh

| Этап | Действие |
|---|---|
| Проверки | Docker, Compose v2, доступность демона, свободное место |
| `.env` | создаёт из `.env.example`, генерирует `APP_SECRET_KEY`, `POSTGRES_PASSWORD`, `ENCRYPTION_KEY` |
| Валидация | падает, если секреты остались шаблонными |
| Эмбеддинги | проверяет доступность `EMBEDDING_SERVICE_URL` (предупреждение, не ошибка) |
| Сборка | `docker compose build` |
| Запуск | `docker compose up -d` |
| Ожидание | Postgres (pg_isready), Backend (health), Frontend (HTTP 200) |
| Токен | создаёт первый API-токен, сохраняет в `.first-token.txt` |
| Отчёт | печатает адреса и полезные команды |

Аргументов нет. Повторный запуск безопасен: существующий `.env` не перезаписывается,
загруженные образы переиспользуются.

## Ручной путь (если скрипт не подходит)

### 1. Требования

| Ресурс | Минимум | Рекомендуется |
|---|---|---|
| RAM | 2 ГБ | 4 ГБ |
| Диск | 5 ГБ | 10 ГБ |
| CPU | 2 ядра | 4 ядра |
| ОС | любая с Docker | Ubuntu 22.04+ |

### 2. Docker

    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker

### 3. Клонирование

    git clone git@github.com:john252525/tp-20260831-tender-deploy.git
    cd tp-20260831-tender-deploy

### 4. Настройка .env

    cp .env.example .env

Заполнить:

**Секреты** (сгенерировать):

    openssl rand -hex 32                                  # APP_SECRET_KEY
    openssl rand -hex 16                                  # POSTGRES_PASSWORD
    python3 -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"   # ENCRYPTION_KEY

**LLM** (ключ DeepSeek):

    LLM_API_KEY=sk-...
    LLM_API_BASE=https://api.deepseek.com
    LLM_MODEL_CHAT=deepseek-v4-flash

**Эмбеддинги** (адрес сервиса Ollama, см. репозиторий tp-20260831-tender-ollama):

    EMBEDDING_SERVICE_URL=http://<IP-сервера-ollama>:11434
    LLM_MODEL_EMBEDDING=nomic-embed-text
    LLM_EMBEDDING_DIMENSIONS=768

**Почта**:

    SMTP_HOST=smtp.mail.ru
    SMTP_PORT=465
    SMTP_USER=robot@example.ru
    SMTP_PASSWORD=...
    SMTP_USE_TLS=false

    IMAP_HOST=imap.mail.ru
    IMAP_PORT=993
    IMAP_USER=robot@example.ru
    IMAP_PASSWORD=...

### 5. Сборка и запуск

    docker compose build
    docker compose up -d

Миграции применяются автоматически: в `backend/entrypoint.sh` вызывается
`alembic upgrade head` перед стартом uvicorn.

### 6. Проверка

    docker compose ps
    curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:18080/api/v1/system/health

Ожидаемый код: `200` (без токена) или `401` (эндпоинт защищён). Оба означают,
что приложение живо. Код `000` — не поднялось, смотреть логи:

    docker compose logs backend --tail 50

### 7. Первый API-токен

    docker compose exec -T backend python -m app.cli.token_cli create --description "admin"

Полученный токен используется в заголовке `X-API-Token`:

    curl -H "X-API-Token: <токен>" http://127.0.0.1:18080/api/v1/tenders/stats

## Доступ снаружи

| Сервис | Адрес | Комментарий |
|---|---|---|
| Frontend | `0.0.0.0:18081` | публикуется на все интерфейсы, раздаёт UI и проксирует `/api/` |
| Backend | `127.0.0.1:18080` | только localhost, доступ через frontend-прокси |
| Postgres | `127.0.0.1:18400` | только localhost |
| MinIO | `0.0.0.0:9000`, консоль `9001` | публикуется, но код пишет в локальную папку |

Открыть в firewall нужно только `18081` (и `9001`, если нужна консоль MinIO):

    ufw allow 18081/tcp

## Порты

Меняются в `.env`: `BACKEND_PORT`, `FRONTEND_PORT`, `POSTGRES_PORT`.
После смены — `docker compose up -d`.

## Структура сервисов

| Сервис | Назначение |
|---|---|
| `backend` | FastAPI, применяет миграции при старте |
| `frontend` | nginx, раздаёт собранный React, проксирует `/api/` |
| `postgres` | PostgreSQL 18 + pgvector |
| `redis` | брокер и backend для Celery |
| `worker` | Celery worker, выполняет задачи |
| `worker-beat` | планировщик, запускает периодические задачи |
| `minio` | S3-хранилище (код пока пишет в локальную папку) |

## Обновление

    git pull
    docker compose build
    docker compose up -d

Миграции применятся автоматически при старте backend. Если менялся
`celery_app.py` — планировщик нужно перечитать:

    docker compose restart worker-beat

## Деплой изменений в коде

**Критично.** В проекте нет бинд-маунтов: код копируется в образ через `COPY`.
Поэтому:

- правка файла в репозитории **не влияет** на работающий контейнер
- `docker compose cp` работает до первого пересоздания контейнера
- после `docker compose up -d` контейнеры пересоздаются из образов,
  и все правки, сделанные через `cp`, теряются

Правильный порядок:

    docker compose build backend worker worker-beat
    docker compose up -d --no-deps backend worker worker-beat

## Резервная копия БД

    docker compose exec -T postgres pg_dump -U tender_user tender_pipeline \
      | gzip > backup-$(date +%Y%m%d-%H%M).sql.gz

Восстановление:

    gunzip -c backup-XXXXXXXX.sql.gz \
      | docker compose exec -T postgres psql -U tender_user -d tender_pipeline

## Подключение внешнего сервиса эмбеддингов

Эмбеддинги считает отдельный сервис (репозиторий `tp-20260831-tender-ollama`).

В `.env` тендерного проекта:

    EMBEDDING_SERVICE_URL=http://<IP-сервера-ollama>:11434

На сервере Ollama разрешить IP тендерного сервера:

    ./scripts/firewall.sh allow <IP-тендерного-сервера>

Проверка связи:

    docker compose exec -T backend python -c "
    import asyncio
    from app.services.embedding_service import generate_embedding
    async def main():
        v = await generate_embedding('проверка')
        print('размерность:', len(v))
    asyncio.run(main())
    "

Ожидаемо: `размерность: 768`.

Если сервис недоступен, проект всё равно работает — семантический фильтр
пропускается, тендеры остаются в `UNCERTAIN` для повторной обработки.

## Типовые проблемы

| Симптом | Причина | Решение |
|---|---|---|
| `docker compose up` падает: `no configuration file` | запуск не из корня репозитория | `cd` в корень, где лежит `docker-compose.yml` |
| Backend не стартует, в логах `Can't locate revision` | образ собран со старыми миграциями | `docker compose build backend && docker compose up -d --no-deps backend` |
| `port is already allocated` | порт занят | сменить `BACKEND_PORT` / `FRONTEND_PORT` в `.env` |
| Backend отвечает, но карточки тендеров пустые | не применены миграции | `docker compose exec backend alembic upgrade head` |
| Тендеры в `UNCERTAIN` с ошибкой эмбеддингов | недоступен сервис Ollama | проверить `EMBEDDING_SERVICE_URL`, firewall на сервере Ollama |
| Задачи висят в `PENDING` | воркер не запущен или задание потеряно | `docker compose ps`, задача `requeue_stuck_tasks_task` подхватит за 15 минут |
| Письма не отправляются | неверные `SMTP_*` | проверить лог `docker compose logs worker | grep send_sync_failed` |
| Ответы поставщиков не приходят | неверные `IMAP_*` или ящик | проверить `docker compose logs worker | grep receive_sync_failed` |
| `no space left on device` | мало диска | `docker system prune -a`, проверить `df -h` |

## Диагностика

    # состояние сервисов
    docker compose ps

    # логи конкретного сервиса
    docker compose logs -f backend
    docker compose logs -f worker
    docker compose logs -f worker-beat

    # ошибки за последнее время
    docker compose logs backend --since 1h | grep -i error

    # проверка БД
    docker compose exec -T postgres psql -U tender_user -d tender_pipeline -c "select count(*) from tenders;"

    # воронка по статусам
    docker compose exec -T postgres psql -U tender_user -d tender_pipeline -c \
      "select status, count(*) from tenders group by status order by count(*) desc;"

    # состояние задач Celery
    docker compose exec -T postgres psql -U tender_user -d tender_pipeline -c \
      "select task_type, status, count(*) from tasks group by task_type, status;"

## Остановка и удаление

    docker compose stop          # остановить, данные сохраняются
    docker compose down          # удалить контейнеры, данные в volumes остаются
    docker compose down -v       # удалить ВСЁ, включая БД и файлы
