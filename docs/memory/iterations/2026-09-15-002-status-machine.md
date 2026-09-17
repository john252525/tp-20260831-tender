# Iteration 002 — Обработка тендера и статусная машина
Date: 2026-09-15

## Goal
Обработка висела на недоступных документах, LLM затирал позиции из API,
READY_FOR_DECISION не выставлялся нигде.

## Changes
- backend/app/services/tender_processor.py — таймауты 12с/5с, статус SKIPPED,
  _positions_text, LLM только если позиций нет, защита APPROVED и REJECTED
- backend/app/services/tender_status_service.py (новый) — recalculate_tender_status
- backend/app/api/v1/tenders.py — поставщики в карточке тендера
- backend/app/services/cp_parser.py, negotiation_service.py, workers/tasks.py —
  вызов пересчёта статуса

## Tests
- backend/tests/test_tender_status_service.py (8 тестов)
- backend/tests/test_tender_processor.py (+2 теста)

## Notes / next
- Лучшее КП выбирается по полноте (FULL > PARTIAL > NONE), затем по марже
