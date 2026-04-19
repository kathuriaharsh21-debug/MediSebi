#!/bin/bash
set -e

echo "=========================================="
echo "  MediSebi Backend — Starting..."
echo "=========================================="

# Default values
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8000}"
export WORKERS="${WORKERS:-4}"

echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Workers: $WORKERS"
echo "  Environment: ${ENVIRONMENT:-development}"
echo "=========================================="

# Create tables on first run (for SQLite)
if [ "${ENVIRONMENT}" != "production" ] || [ "${DATABASE_URL%%:*}" = "sqlite" ]; then
    echo "  Running database migrations..."
    python -c "from app.models import Base; from app.core.database import get_engine; Base.metadata.create_all(bind=get_engine())"
fi

# Start server
if [ "${WORKERS}" = "1" ]; then
    uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
else
    uvicorn app.main:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
fi
