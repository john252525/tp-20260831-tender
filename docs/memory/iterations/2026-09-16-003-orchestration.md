# Iteration 003 — Автооркестрация
Date: 2026-09-16

## Goal
beat_schedule состоял из одной задачи. 23 задачи висели в PENDING навсегда,
891 тендер в NEW никто не обрабатывал.

## Changes
- backend/app/workers/celery_app.py — 8 задач вместо 1
- backend/app/workers/tasks.py — sync_active_sources_task, process_new_tenders_task,
  requeue_stuck_tasks_task, reprocess_unenriched_tenders_task,
  start_pipeline_for_scored_tenders_task, TASK_RUNNERS
- backend/app/services/tender_sync_service.py — убрана заглушка (создавала
  10 фальшивых тендеров), max_pages 10 -> 1

## Tests
- Проверено: requeued=17, process_new_tenders candidates=50 started=50

## Notes / next
- Присмотр за задачами не работал: runner.delay вместо runner(),
  и AsyncResult для потерянной задачи возвращает PENDING
- worker-beat был в крашлупе (нет миграции 010), пересобран
