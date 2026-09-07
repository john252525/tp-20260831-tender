#!/bin/sh
set -e

# Применяем миграции Alembic
alembic upgrade head

# Запускаем переданную команду
exec "$@"
