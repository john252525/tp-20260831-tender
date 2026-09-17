# Iteration 004 — Маржа, напоминания, торг
Date: 2026-09-16

## Goal
Маржа была заглушкой 50 для всех. Напоминания и торг не отправлялись,
хотя шаблоны и настройки в БД были.

## Changes
- backend/app/services/scoring_service.py — _calculate_margin_score,
  _margin_to_score; источники: КП, категория, fallback; только FULL и PARTIAL
- backend/app/services/decision_service.py — пороги из настроек
- backend/app/services/negotiation_service.py — send_reminders, request_discounts,
  run_negotiation теперь реально вызывает send_email

## Tests
- backend/tests/test_scoring_service.py (7), test_reminders.py (3), test_discounts.py (2)

## Notes / next
- Флаг reminders_dry_run для безопасной проверки отправки
- SMTP проверен реальной отправкой себе
