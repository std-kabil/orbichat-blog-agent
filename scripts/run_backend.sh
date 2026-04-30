#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"

APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8000}"
LOG_DIR="${LOG_DIR:-${PROJECT_DIR}/.logs}"

START_DEPS=1
RUN_MIGRATIONS=1
INSTALL_EDITABLE=1
START_API=1
START_WORKER=1
START_BEAT=1

usage() {
  cat <<EOF
Run the OrbiChat Blog Agent backend locally.

Usage:
  ./scripts/run_backend.sh [options]

Options:
  --no-deps            Do not start PostgreSQL/Redis with docker compose.
  --no-migrations      Do not run alembic upgrade head.
  --no-install         Do not run python -m pip install -e .
  --api-only           Start only the FastAPI server.
  --worker-only        Start only the Celery worker.
  --beat-only          Start only Celery beat.
  --host HOST          FastAPI host. Default: ${APP_HOST}
  --port PORT          FastAPI port. Default: ${APP_PORT}
  -h, --help           Show this help.

Environment:
  APP_HOST             FastAPI host override.
  APP_PORT             FastAPI port override.
  LOG_DIR              Log directory. Default: ${LOG_DIR}

Examples:
  ./scripts/run_backend.sh
  ./scripts/run_backend.sh --no-deps --no-install
  APP_PORT=8010 ./scripts/run_backend.sh --api-only
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-deps)
      START_DEPS=0
      shift
      ;;
    --no-migrations)
      RUN_MIGRATIONS=0
      shift
      ;;
    --no-install)
      INSTALL_EDITABLE=0
      shift
      ;;
    --api-only)
      START_API=1
      START_WORKER=0
      START_BEAT=0
      shift
      ;;
    --worker-only)
      START_API=0
      START_WORKER=1
      START_BEAT=0
      shift
      ;;
    --beat-only)
      START_API=0
      START_WORKER=0
      START_BEAT=1
      shift
      ;;
    --host)
      APP_HOST="${2:?--host requires a value}"
      shift 2
      ;;
    --port)
      APP_PORT="${2:?--port requires a value}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "Docker Compose is required to start PostgreSQL/Redis. Re-run with --no-deps if they are already running." >&2
    exit 1
  fi
}

wait_for_python_check() {
  local label="$1"
  local code="$2"
  local attempts="${3:-60}"

  echo "Waiting for ${label}..."
  for ((i = 1; i <= attempts; i++)); do
    if python - "$code" >/dev/null 2>&1 <<'PY'
import sys

code = sys.argv[1]
exec(code)
PY
    then
      echo "${label} is ready."
      return 0
    fi
    sleep 1
  done

  echo "Timed out waiting for ${label}." >&2
  exit 1
}

stop_children() {
  local exit_code=$?

  trap - INT TERM EXIT

  if [[ ${#PIDS[@]} -gt 0 ]]; then
    echo
    echo "Stopping backend processes..."
    for pid in "${PIDS[@]}"; do
      if kill -0 "${pid}" >/dev/null 2>&1; then
        kill "${pid}" >/dev/null 2>&1 || true
      fi
    done
    wait "${PIDS[@]}" >/dev/null 2>&1 || true
  fi

  exit "${exit_code}"
}

PIDS=()
trap stop_children INT TERM EXIT

require_command python

if [[ ! -f ".env" && -f ".env.example" ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Add API keys there for real agent runs."
fi

if [[ "${INSTALL_EDITABLE}" -eq 1 ]]; then
  echo "Installing backend package in editable mode..."
  python -m pip install -e .
fi

if [[ "${START_DEPS}" -eq 1 ]]; then
  require_command docker
  echo "Starting PostgreSQL and Redis..."
  docker_compose up -d postgres redis
fi

wait_for_python_check "PostgreSQL" "import psycopg; psycopg.connect('postgresql://postgres:postgres@localhost:5432/orbichat_blog_agent').close()"
wait_for_python_check "Redis" "import redis; redis.Redis.from_url('redis://localhost:6379/0').ping()"

if [[ "${RUN_MIGRATIONS}" -eq 1 ]]; then
  echo "Running database migrations..."
  python -m alembic upgrade head
fi

mkdir -p "${LOG_DIR}"

start_process() {
  local name="$1"
  shift
  local log_file="${LOG_DIR}/${name}.log"

  echo "Starting ${name}. Logs: ${log_file}"
  "$@" >"${log_file}" 2>&1 &
  PIDS+=("$!")
}

if [[ "${START_API}" -eq 1 ]]; then
  start_process "api" python -m uvicorn app.main:app --host "${APP_HOST}" --port "${APP_PORT}" --reload
fi

if [[ "${START_WORKER}" -eq 1 ]]; then
  start_process "celery-worker" celery -A jobs.celery_app worker --loglevel=info
fi

if [[ "${START_BEAT}" -eq 1 ]]; then
  start_process "celery-beat" celery -A jobs.celery_app beat --loglevel=info
fi

echo
echo "Backend is running."
if [[ "${START_API}" -eq 1 ]]; then
  echo "API: http://127.0.0.1:${APP_PORT}"
  echo "Health: http://127.0.0.1:${APP_PORT}/health"
fi
echo "Press Ctrl-C to stop FastAPI/Celery processes."
echo

while true; do
  for pid in "${PIDS[@]}"; do
    if ! kill -0 "${pid}" >/dev/null 2>&1; then
      echo "A backend process exited. Check logs in ${LOG_DIR}." >&2
      exit 1
    fi
  done
  sleep 2
done
