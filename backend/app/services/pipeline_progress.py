"""Утилита для обновления прогресса пайплайна через отдельную сессию БД."""
import structlog
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.models.task import Task

logger = structlog.get_logger()


async def update_pipeline_steps(
    task_id: str,
    steps: List[dict],
    percent: float,
    status: str = 'IN_PROGRESS',
    error: Optional[str] = None,
    result_summary: Optional[str] = None,
):
    """Полностью перезаписывает состояние шагов пайплайна в Task."""
    try:
        async with AsyncSessionLocal() as session:
            task = await session.get(Task, UUID(task_id))
            if not task:
                logger.warning('pipeline_progress.task_not_found', task_id=task_id)
                return
            task.output_data = {'steps': steps}
            task.progress_percent = percent
            if error:
                task.status = 'FAILED'
                task.error_message = str(error)[:2000]
                task.completed_at = datetime.now(timezone.utc)
            elif status:
                task.status = status
            if result_summary:
                task.result_summary = result_summary
            await session.commit()
    except Exception as exc:
        logger.error('pipeline_progress.update_failed', task_id=task_id, error=str(exc))


async def complete_pipeline_task(task_id: str, result_summary: str):
    """Завершает задачу пайплайна через отдельную сессию."""
    try:
        async with AsyncSessionLocal() as session:
            task = await session.get(Task, UUID(task_id))
            if not task:
                return
            task.status = 'COMPLETED'
            task.progress_percent = 100.0
            task.completed_at = datetime.now(timezone.utc)
            task.result_summary = result_summary
            await session.commit()
    except Exception as exc:
        logger.error('pipeline_progress.complete_failed', task_id=task_id, error=str(exc))
