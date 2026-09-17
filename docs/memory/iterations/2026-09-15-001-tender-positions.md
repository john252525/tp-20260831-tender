# Iteration 001 — Позиции и документы закупки
Date: 2026-09-15

## Goal
Тендеры импортировались без состава закупки: 0 позиций, 0 документов. 350 тендеров в ERROR.

## Changes
- backend/app/services/gosplan_positions.py (новый) — разбор notificationInfo:
  позиции, документы, условия, заказчик. 4 варианта упаковки ответа
- backend/app/services/tender_sync_service.py — enrich_tender_from_purchase,
  фильтр is_source_sync_supported
- backend/app/api/v1/tenders.py — GET /tenders/{id} отдаёт positions, documents,
  requirements; список считает positions_count и documents_count
- frontend/src/pages/TenderDetailPage.tsx — чтение tender.positions

## Tests
- backend/tests/test_gosplan_positions.py (9 тестов) на живых фикстурах ГосПлан

## Notes / next
- Причина: doc.get(url) вместо docs[].source.attachmentsInfo.attachmentInfo[].url
- Позиции есть в API, LLM и скачивание файлов не нужны
