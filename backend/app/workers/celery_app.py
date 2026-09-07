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
    'receive-emails-every-5-minutes': {
        'task': 'app.workers.tasks.receive_emails_task',
        'schedule': 300.0,
    },
}
