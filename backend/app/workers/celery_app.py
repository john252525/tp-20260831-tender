from celery import Celery
from app.core.config import settings

celery_app = Celery(
    'tender_pipeline',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['app.workers.tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

celery_app.set_default()

celery_app.conf.beat_schedule = {
    # Приём входящих писем от поставщиков
    'receive-emails-every-5-minutes': {
        'task': 'app.workers.tasks.receive_emails_task',
        'schedule': 300.0,
    },
    # Синхронизация активных источников тендеров (по их poll_interval_minutes)
    'sync-active-sources-every-5-minutes': {
        'task': 'app.workers.tasks.sync_active_sources_task',
        'schedule': 300.0,
    },
    # Автоматическая обработка новых тендеров
    'process-new-tenders-every-10-minutes': {
        'task': 'app.workers.tasks.process_new_tenders_task',
        'schedule': 600.0,
    },
    # Присмотр за зависшими задачами (потерянными в очереди)
    'requeue-stuck-tasks-every-15-minutes': {
        'task': 'app.workers.tasks.requeue_stuck_tasks_task',
        'schedule': 900.0,
    },
    # Восстановление тендеров, упавших из-за отсутствия данных
    'reprocess-unenriched-tenders-every-30-minutes': {
        'task': 'app.workers.tasks.reprocess_unenriched_tenders_task',
        'schedule': 1800.0,
    },
    # Лучшие по скору тендеры уходят в полный конвейер
    'start-pipeline-for-scored-every-15-minutes': {
        'task': 'app.workers.tasks.start_pipeline_for_scored_tenders_task',
        'schedule': 900.0,
    },
    # Напоминания поставщикам, не ответившим на запрос КП
    'send-reminders-every-30-minutes': {
        'task': 'app.workers.tasks.send_reminders_task',
        'schedule': 1800.0,
    },
    # Торг: запрос улучшения цен у поставщиков с завышенными КП
    'request-discounts-every-30-minutes': {
        'task': 'app.workers.tasks.request_discounts_task',
        'schedule': 1800.0,
    },
}
