# PROJECT

Что за продукт, для кого, как устроен. Меняется редко, читается всегда.

## Суть

Автоматизированный посредник между государственными закупками и оптовыми поставщиками.
Система импортирует тендеры, находит выгодные по марже и простоте, подбирает поставщиков,
сама запрашивает у них цены, разбирает ответы, торгуется и передаёт человеку готовую сделку.

**Прибыль** = НМЦК закупки минус цена поставщика.

## Требования заказчика (дословно)

> У меня есть доступ к API всех российских тендеров (их там миллионы) (список тендеров и поиск
> по ним, просмотр каждого конкретного тендера со списком прилагающихся к нему подробно
> описывающих закупку документов). Среди этой массы тендеров надо автоматически находить лучшие
> по прибыли и простоте/скорости поставки, автоматически гуглить под них поставщиков,
> автоматически связываться/списываться с ними запрашивать условия и цены на списки конкретно
> интересующих нас товарных позиций, автоматически получать и парсить ответы, автоматически
> анализировать проходимость, в случае недостатка присланной инфы автоматически
> перезапросить/уточнить недостающую инфу и добиться лучших условий и цен. Лучшие из лучших
> найденных и полностью согласованных передать в исполнение человеку.

## Разложение на шаги

| # | Шаг | Компонент |
|---|-----|-----------|
| 1 | Список тендеров и поиск | `GET /tenders`, `TendersPage` |
| 2 | Просмотр тендера и документов | `GET /tenders/{id}`, `TenderDetailPage` |
| 3 | Поиск лучших по прибыли и простоте | `scoring_service`, `tender_status_service` |
| 4 | Поиск поставщиков | `supplier_search`, внешний search API |
| 5 | Связь с поставщиками, запрос цен | `pipeline_service` → `outgoing_drafts` → `send_email` |
| 6 | Получение и разбор ответов | IMAP-задача, `cp_parser` (LLM) |
| 7 | Анализ проходимости | `risk_service`, `decision_service` |
| 8 | Дозапрос и торг | `negotiation_service` |
| 9 | Передать человеку | `READY_FOR_DECISION` → `POST /decisions/{id}/approve` |

## Стек

| Слой | Технологии |
|---|---|
| Backend | Python 3.12, FastAPI 0.115, SQLAlchemy 2.0 (async), Alembic, Celery 5.4, structlog |
| БД | PostgreSQL + pgvector (эмбеддинги 768) |
| Очереди | Redis 7 (broker и backend Celery) |
| Frontend | React 18, TypeScript, Vite, Tailwind, TanStack Query, Recharts, nginx |
| Файлы | MinIO (поднят, код пишет в локальную папку — техдолг) |
| LLM | DeepSeek `deepseek-v4-flash` (`api.deepseek.com`) |
| Эмбеддинги | Ollama `nomic-embed-text`, вынесена в отдельный сервис |

## Внешние интеграции

| Что | Откуда | Почему так |
|---|---|---|
| Тендеры | ГосПлан API `v2test.gosplan.info` (тест), `v2.gosplan.info` (прод, нужен ключ) | `zakupki.gov.ru` недоступен с хоста, ГосПлан — агрегатор |
| Состав закупки | `notificationInfo` в детальном ответе ГосПлан | позиции, цены, ОКПД2 есть в API, LLM и скачивание файлов не нужны |
| Поиск поставщиков | `2222.apitter.com/search/api.php` | замена Google CSE (ключей нет) |
| LLM | DeepSeek | ключ есть, дешёвый |
| Эмбеддинги | внешний Ollama `http://199.189.253.227:11434` | вынесен, чтобы не конкурировать за память |
| Почта | mail.ru, SMTP 465, IMAP 993 | рабочий ящик в `.env` |

## Архитектура: сквозной конвейер

Шаг 1. Синхронизация: `sync_tenders_from_source(source_id)`
- `GosPlanClient.search_purchases()` — список закупок, пагинация, троттлинг
- `GosPlanClient.get_purchase(num)` — детали по каждой закупке
- `enrich_tender_from_purchase()` — позиции, документы, условия, заказчик

Шаг 2. Обработка: `process_tender(tender_id)`
- `_ensure_tender_enriched()` — добор состава для старых записей
- `_load_documents()` — best-effort, статус SKIPPED если файл недоступен
- `_semantic_filter()` — сравнение эмбеддинга тендера с категориями
- `_extract_tender_structure()` — LLM, только если позиций ещё нет
- `calculate_score()` — маржа, простота, объём, конкурентность

Шаг 3. Конвейер: `run_full_pipeline_for_tender()`
- `generate_search_queries()` — LLM генерирует поисковые запросы
- `search_suppliers_with_queries()` — внешний поиск и внутренняя база
- `crawl_multiple_sites()` — email с сайтов поставщиков
- создание `outgoing_drafts`

Шаг 4. Отправка: `send_drafts` — РУЧНОЙ шаг через UI
- `send_email()`, запись `Communication(cp_request)`, `lot.status = CP_REQUESTED`

Шаг 5. Приём: `receive_emails_task` каждые 5 минут
- IMAP, матчинг по In-Reply-To, создание `CommercialOffer`, запуск `parse_cp_task`

Шаг 6. Разбор КП: `parse_cp(cp_id)` через LLM
- позиции, цены, сроки, НДС, условия оплаты, coverage, margin_percent

Шаг 7. Пересчёт статуса: `recalculate_tender_status()`

Шаг 8. Удержание: `send_reminders_task`, `request_discounts_task` каждые 30 минут

## Статусная машина

НОВЫЙ -> PROCESSING -> RELEVANT / UNCERTAIN / NOT_RELEVANT
                  -> SCORING -> SCORED
                  -> AWAITING_CP -> CP_REQUESTED -> CP_PARTIALLY_RECEIVED
                  -> CP_FULLY_RECEIVED -> READY_FOR_DECISION
                  -> APPROVED / REJECTED / NEEDS_MORE_INFO
                  -> ERROR

Правила:
- APPROVED и REJECTED защищены, process_tender их не трогает
- статусы CP_*, NEGOTIATING, READY_FOR_DECISION выставляются только через
  tender_status_service.recalculate_tender_status()
- READY_FOR_DECISION требует: все лоты закрыты полными КП, маржа не ниже
  min_margin_percent, риск не выше max_risk_level

## Расписание Celery beat

- receive_emails_task, 5 мин — приём писем поставщиков
- sync_active_sources_task, 5 мин — синхронизация источников по poll_interval_minutes
- process_new_tenders_task, 10 мин — обработка тендеров в NEW
- requeue_stuck_tasks_task, 15 мин — перезапуск зависших в PENDING
- reprocess_unenriched_tenders_task, 30 мин — восстановление упавших без данных
- start_pipeline_for_scored_tenders_task, 15 мин — конвейер для лучших по скору
- send_reminders_task, 30 мин — напоминания не ответившим
- request_discounts_task, 30 мин — торг с завысившими цену

## Карта кода

### backend/app/services/ — бизнес-логика

- gosplan_client.py — клиент ГосПлан: троттлинг 0.7с, 5 попыток, Retry-After
- gosplan_positions.py — разбор состава закупки из notificationInfo (4 варианта упаковки)
- tender_sync_service.py — синхронизация, enrich_tender_from_purchase, фильтр источников
- tender_processor.py — обработка: обогащение, документы, семантика, структура, скоринг
- tender_status_service.py — пересчёт статуса из фактов, защита ручных решений
- scoring_service.py — скор: маржа (КП, категория, fallback), простота, объём, конкурентность
- supplier_search.py — поиск поставщиков, фильтр маркетплейсов, имя из домена
- website_crawler.py — сбор email: только домен сайта, отсев сервисных и непрофильных
- pipeline_service.py — полный конвейер для тендера
- cp_parser.py — LLM-разбор КП, coverage, маржа, clarification_items
- negotiation_service.py — send_reminders, request_discounts, run_negotiation
- email_service.py — SMTP-отправка, IMAP-приём
- decision_service.py — авто-рекомендация APPROVE / REVIEW / REJECT
- risk_service.py — оценка риска: цена, дедлайн, история поставщика
- embedding_service.py — эмбеддинги через внешний Ollama
- llm_service.py — DeepSeek: структура, запросы, классификация
- document_parser.py — текст из PDF, DOCX, XLSX
- s3_service.py — ЗАГЛУШКА: локальная папка /app/data

### backend/app/workers/

- celery_app.py — приложение Celery и beat_schedule
- tasks.py — все Celery-задачи, словарь TASK_RUNNERS

### backend/app/api/v1/ — более 60 эндпоинтов

Роутеры: system, tokens, settings, categories, tasks, tender_sources, tenders,
suppliers, communications, commercial_offers, decisions, negotiations

Ключевые:
- GET /tenders — список с фильтрами, positions_count, documents_count
- GET /tenders/{id} — карточка: позиции, документы, условия, поставщики
- POST /tenders/{id}/run-pipeline — запуск конвейера
- GET/POST /tenders/{id}/drafts — черновики и отправка
- POST /decisions/{id}/approve | reject | request-info

### frontend/src/ — 22 страницы

Ключевые: TendersPage, TenderDetailPage (9 вкладок), PipelinePage, DecisionsPage,
SuppliersPage, SourcesPage, ScoringPage, TemplatesPage

## Модель данных (20 таблиц)

Ядро:
- tenders — source_tender_id, title, description, nmck, deadline_at, customer_*, status,
  score, score_components, embedding (pgvector 768), matched_category_id, similarity_score,
  final_margin_percent, selected_supplier_id, processing_error, search_queries, structured_data
- tender_positions — position_number, name, characteristics, gost, okpd2, quantity, unit
- tender_documents — filename, file_size_bytes, mime_type, source_url, parsed_text, parse_status
- tender_requirements — delivery_*, license_required, sro_required, security_*, stages_count
- tender_status_history — status, previous_status, note, set_at (поля created_at НЕТ)

Источники и категории:
- tender_sources — name, type, api_url, api_key_encrypted, config (page_size, max_pages),
  is_active, last_sync_at, last_sync_status, last_error
- categories — name, keywords, embedding

Поставщики:
- suppliers — name, type, website, email, phone, inn, tags, successful_deals, rating
- lot_suppliers — статус лота: PENDING / CP_REQUESTED / CP_RECEIVED / NO_RESPONSE / NEGOTIATING

Коммуникации и предложения:
- communications — direction, channel, subject, body_text, message_type,
  external_id (Message-ID), in_reply_to_external_id, sent_at, received_at
- communication_attachments — filename, storage_path, is_parsed
- commercial_offers — status (PROCESSING / FULL / PARTIAL / NONE / ERROR), coverage,
  total_cost_with_all, margin_absolute, margin_percent, clarification_needed, clarification_items
- offer_positions — tender_position_id, match_type (exact / analog / not_found), price_per_unit

Решения и служебное:
- decisions — decision (APPROVED / REJECTED / NEEDS_MORE_INFO), chosen_supplier_id,
  chosen_offer_id, margin_at_decision, reason
- outgoing_drafts — supplier_website, supplier_name, email, subject, body_text, status (draft / sent)
- tasks — task_type, status, entity_type, entity_id, celery_task_id, progress_percent,
  input_data, output_data
- settings и settings_history — настройки по секциям и история
- api_tokens — token, description, rate_limit_per_minute, is_active

Миграции: 001_initial ... 010_add_tender_search_queries

## Настройки в БД по секциям

- scoring — min_total_score (60), min_margin_percent (15), max_risk_level (MEDIUM),
  веса margin / simplicity / volume / competition, volume_thresholds, volume_scores
- communication — reminder_after_hours (24), response_timeout_hours (48),
  max_discount_requests_per_supplier (2), max_suppliers_per_lot (10),
  price_diff_threshold_percent (5), email_config
- templates — cp_request, cp_reminder, clarification, discount_request
- company — реквизиты и подпись для писем
- filters — min_similarity_accept (0.75), min_similarity_uncertain (0.6)
- ml — заготовки для будущего ML

## Порты и запуск

| Сервис | Порт |
|---|---|
| Backend API | 127.0.0.1:18080 |
| Frontend | 0.0.0.0:18081 |
| PostgreSQL | 127.0.0.1:18400 |
| MinIO | 9000 (API), 9001 (консоль) |
| Ollama (внешний) | 199.189.253.227:11434 |

Сервисы docker compose: backend, frontend, postgres, redis, worker, worker-beat, minio.
Локальный ollama закомментирован как аварийный резерв.

Аутентификация API: заголовок X-API-Token, токены через CLI token_cli.

## Ограничения окружения

1. zakupki.gov.ru недоступен с хоста (ConnectTimeout и с хоста, и из контейнера).
   Файлы документов не скачиваются, parse_status=SKIPPED. Обходится тем, что состав
   закупки берётся из ГосПлан API.

2. Критическая нехватка памяти на хосте: 3805 МБ всего, swap занят полностью,
   Committed_AS около 16 ГБ от чужих проектов. Ollama вынесена в отдельный сервис,
   чтобы убрать крупнейшего потребителя памяти.

3. Playwright работает, но только С ХОСТА, не из контейнера. На хосте (Ubuntu 26.04,
   glibc) браузеры уже установлены: /root/.cache/ms-playwright/chromium_headless_shell-1234.
   В alpine-контейнерах запускать нельзя: musl несовместим с бинарниками Chrome
   (ошибка «Executable doesn't exist»). Полный chromium на тяжёлых страницах падает
   по OOM, headless shell — нет.

   Рабочий запуск:

       cd frontend && node e2e/live-card-check.cjs

   Проверки на реальном ответе API без браузера остаются: jest плюс jsdom.

4. Docker образы без бинд-маунтов: правки кода требуют пересборки (docker compose build).
