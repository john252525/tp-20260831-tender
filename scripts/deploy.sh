#!/usr/bin/env bash
# Деплой тендерного проекта. Идемпотентен: повторный запуск не ломает рабочее состояние.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

log()  { printf "==> %s\n" "$*"; }
warn() { printf "ВНИМАНИЕ: %s\n" "$*" >&2; }
die()  { printf "ОШИБКА: %s\n" "$*" >&2; exit 1; }

# Значение ключа из .env (безопасный разбор, без source)
env_value() {
  [ -f .env ] || return 0
  grep -E "^$1=" .env | head -1 | cut -d= -f2- | tr -d '"'
}

# ---------------------------------------------------------------- проверки

command -v docker >/dev/null 2>&1 || die "Docker не установлен"
docker compose version >/dev/null 2>&1 || die "Docker Compose (v2) не найден"

if ! docker info >/dev/null 2>&1; then
  die "Docker демон недоступен. Запустите: systemctl start docker"
fi

# Порты берём из .env, чтобы проверки совпадали с compose
BACKEND_PORT="$(env_value BACKEND_PORT)";   BACKEND_PORT="${BACKEND_PORT:-18080}"
FRONTEND_PORT="$(env_value FRONTEND_PORT)"; FRONTEND_PORT="${FRONTEND_PORT:-18081}"
POSTGRES_PORT="$(env_value POSTGRES_PORT)"; POSTGRES_PORT="${POSTGRES_PORT:-18400}"

# Свободное место: сборка образов и работа БД требуют запаса
AVAIL_KB=$(df -Pk . | awk "NR==2 {print \$4}")
if [ "$AVAIL_KB" -lt 3145728 ]; then
  warn "мало свободного места (меньше 3 ГБ). Сборка может упасть"
fi

# ---------------------------------------------------------------- .env

if [ ! -f .env ]; then
  log "Файл .env не найден, создаю из .env.example"
  [ -f .env.example ] || die ".env.example отсутствует"
  cp .env.example .env

  # Генерируем секреты
  SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p -c 64)
  DBPASS=$(openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | xxd -p -c 32)
  ENCKEY=$(python3 -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())" 2>/dev/null || true)

  sed -i "s|^APP_SECRET_KEY=.*|APP_SECRET_KEY=${SECRET}|" .env
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${DBPASS}|" .env
  [ -n "$ENCKEY" ] && sed -i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${ENCKEY}|" .env

  log "Секреты сгенерированы"
  warn "заполните в .env: LLM_API_KEY, SMTP_*, IMAP_*, EMBEDDING_SERVICE_URL"
else
  log "Файл .env найден"
fi

# Проверка, что секреты не остались шаблонными
for key in APP_SECRET_KEY POSTGRES_PASSWORD ENCRYPTION_KEY; do
  val=$(grep -E "^${key}=" .env | head -1 | cut -d= -f2-)
  case "$val" in
    ""|*change-me*|*changeme*)
      die "${key} не заполнен в .env (значение: ${val:-пусто})"
      ;;
  esac
done
log "Секреты заполнены"

# Проверка внешнего сервиса эмбеддингов
EMB_URL=$(grep -E "^EMBEDDING_SERVICE_URL=" .env | cut -d= -f2- || echo "")
if [ -z "$EMB_URL" ]; then
  warn "EMBEDDING_SERVICE_URL не задан, семантический фильтр не будет работать"
elif ! curl -fsS -m 5 "${EMB_URL%/}/api/tags" >/dev/null 2>&1; then
  warn "сервис эмбеддингов недоступен: $EMB_URL"
  warn "проект запустится, но семантический анализ работать не будет"
else
  log "Сервис эмбеддингов доступен: $EMB_URL"
fi

# ---------------------------------------------------------------- сборка

ARCH=$(uname -m)
log "Архитектура: $ARCH"

log "Сборка образов"
docker compose build

# ---------------------------------------------------------------- запуск

log "Запуск сервисов"
docker compose up -d

log "Ожидание готовности Postgres"
for i in $(seq 1 60); do
  if docker compose exec -T postgres pg_isready -U tender_user -d tender_pipeline >/dev/null 2>&1; then
    log "Postgres готов"
    break
  fi
  [ "$i" -eq 60 ] && die "Postgres не поднялся за 120 секунд"
  sleep 2
done

log "Ожидание готовности Backend (миграции применяются в entrypoint)"
HEALTH_OK=0
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 5 http://127.0.0.1:"${BACKEND_PORT:-18080}"/api/v1/system/health 2>/dev/null || echo 000)
  if [ "$code" = "200" ] || [ "$code" = "401" ]; then
    HEALTH_OK=1
    log "Backend отвечает (код $code)"
    break
  fi
  if [ "$i" -eq 60 ]; then break; fi
  sleep 2
done

if [ "$HEALTH_OK" -eq 0 ]; then
  warn "Backend не ответил за 120 секунд. Логи:"
  docker compose logs backend --tail 30
fi

log "Ожидание готовности Frontend"
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 5 http://127.0.0.1:"${FRONTEND_PORT:-18081}"/ 2>/dev/null || echo 000)
  if [ "$code" = "200" ]; then
    log "Frontend отвечает"
    break
  fi
  if [ "$i" -eq 30 ]; then warn "Frontend не ответил за 60 секунд"; break; fi
  sleep 2
done

# ---------------------------------------------------------------- токен

log "Проверка API-токена"
TOKEN_COUNT=$(docker compose exec -T postgres psql -U tender_user -d tender_pipeline -t -A \
  -c "select count(*) from api_tokens where is_active = true;" 2>/dev/null | tr -d "[:space:]" || echo "0")

if [ "${TOKEN_COUNT:-0}" = "0" ]; then
  log "Активных токенов нет, создаю первый"
  TOKEN=$(docker compose exec -T backend python -m app.cli.token_cli create \
    --description "deploy-$(date +%Y%m%d)" 2>/dev/null | grep -oP "Token created: \K\w+" || true)
  if [ -n "${TOKEN:-}" ]; then
    echo "$TOKEN" > .first-token.txt
    log "Токен сохранён в .first-token.txt"
  else
    warn "не удалось создать токен, создайте вручную"
  fi
else
  log "Активных токенов: $TOKEN_COUNT"
fi

# ---------------------------------------------------------------- отчёт

HOST_IP=$(hostname -I 2>/dev/null | awk "{print \$1}" || echo "localhost")
BPORT="${BACKEND_PORT:-18080}"
FPORT="${FRONTEND_PORT:-18081}"

echo
log "Деплой завершён"
echo
echo "  Frontend:   http://${HOST_IP}:${FPORT}"
echo "  Backend:    http://127.0.0.1:${BPORT}"
echo "  API docs:   http://${HOST_IP}:${FPORT}/docs"
echo "  Postgres:   127.0.0.1:${POSTGRES_PORT:-18400}"
echo
echo "  Статус:     docker compose ps"
echo "  Логи:       docker compose logs -f backend worker"
echo "  Токен:      cat .first-token.txt"
echo
