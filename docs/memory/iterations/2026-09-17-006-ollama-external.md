# Iteration 006 — Вынос Ollama в отдельный сервис
Date: 2026-09-17

## Goal
Ollama конкурировала за память с проектом, OOM убивал llama-server,
падал семантический анализ.

## Changes
- Создан репозиторий tp-20260831-tender-ollama (14 файлов): docker-compose,
  скрипты install / healthcheck / firewall / backup / restore, документация
- .env — EMBEDDING_SERVICE_URL на внешний адрес
- docker-compose.yml — убран depends_on ollama, локальный сервис закомментирован
- Образы backend, worker, worker-beat пересобраны

## Tests
- curl снаружи: модель есть; healthcheck: размерность 768
- Эмбеддинг из контейнера: dim=768 за 0.16с
- Семантический фильтр: similarity=0.725, категория «Медицинские изделия»
- 39 тестов проходят

## Notes / next
- Критично: docker compose up -d пересоздавал контейнеры из старых образов,
  правки через docker compose cp терялись. Решение: пересборка образов
- Перенос на реальный сервер ждёт адреса
