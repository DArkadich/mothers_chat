#!/usr/bin/env bash
set -euo pipefail

# smoke_compose_check.sh — безопасный скрипт для проверки docker-compose + alembic + API
# Usage:
#   ENABLE_FAKE_OPENAI=1 ./scripts/smoke_compose_check.sh [--reset-volume]

RESET_VOLUME=0
if [[ ${1:-} == "--reset-volume" ]]; then
  RESET_VOLUME=1
fi

export ENABLE_FAKE_OPENAI=${ENABLE_FAKE_OPENAI:-1}

echo "Project: $(pwd)"

if [[ "$RESET_VOLUME" -eq 1 ]]; then
  echo "Stopping compose and removing volumes (motherschat_db_data)"
  docker compose down -v || true
  docker volume rm motherschat_db_data || true
fi

echo "Starting compose (build if needed)..."
docker compose up -d --build

echo "Waiting for backend to respond on /health..."
for i in {1..30}; do
  if curl -sS http://localhost:8000/health >/dev/null 2>&1; then
    echo "Backend /health OK"
    break
  fi
  echo "Waiting for backend... ($i)"
  sleep 2
done

echo "Backend OpenAPI /api endpoints (first 20):"
curl -sS http://localhost:8000/openapi.json | grep -o '"/api[^"\]*"' | sed -n '1,20p' || true

echo "Checking Alembic state inside backend container"
set +e
docker compose exec backend sh -c 'cd backend && alembic current'
docker compose exec backend sh -c 'cd backend && alembic heads'
docker compose exec backend sh -c 'cd backend && alembic history -n 5'
RET=$?
set -e

if [[ $RET -ne 0 ]]; then
  echo "Alembic commands failed — trying to run upgrade head (after waiting for DB)"
  echo "Waiting for Postgres to be ready..."
  for i in {1..30}; do
    docker compose exec db pg_isready -U motherschat && break || true
    sleep 1
  done
  docker compose exec backend sh -c 'cd backend && alembic upgrade head'
fi

# Insert a smoke assistant if none exists
echo "Ensuring a test assistant exists (code=smoke_test_assistant)"
set +e
EXISTS=$(docker compose exec -T db psql -U motherschat -d motherschat -tAc "SELECT 1 FROM assistants WHERE code='smoke_test_assistant' LIMIT 1;" ) || true
set -e
if [[ -z "$EXISTS" ]]; then
  echo "Inserting smoke assistant into DB"
  docker compose exec -T db psql -U motherschat -d motherschat -c "INSERT INTO assistants (code,title,description,base_model,system_prompt,extra_config) VALUES ('smoke_test_assistant','Smoke test','smoke','gpt-4.1-mini','You are helpful','{}'::jsonb);"
else
  echo "Smoke assistant already exists"
fi

# Create session via API
echo "Creating chat session via API"
SESSION_ID=$(curl -sS -X POST http://localhost:8000/api/chat/session -H "Content-Type: application/json" -d '{"assistant_slug":"smoke_test_assistant","telegram_id":"999"}' | tr -d '\r\n%' | jq -r '.session_id') || true

if [[ -z "$SESSION_ID" || "$SESSION_ID" == "null" ]]; then
  echo "Failed to create session; dumping /api/chat/session response:" 
  curl -sS -X POST http://localhost:8000/api/chat/session -H "Content-Type: application/json" -d '{"assistant_slug":"smoke_test_assistant","telegram_id":"999"}' || true
  exit 1
fi

echo "Session created: $SESSION_ID"

# Send a message (fake OpenAI will reply)
RESP=$(curl -sS -X POST http://localhost:8000/api/chat/send -H "Content-Type: application/json" -d "{\"session_id\": $SESSION_ID, \"assistant_slug\": \"smoke_test_assistant\", \"message\": \"Hello\" }") || true

echo "Response from /api/chat/send:"
echo "$RESP" | jq || echo "$RESP"

echo "Smoke finished"
