#!/bin/bash
set -e

echo "Running Alembic migrations..."
alembic -c src/alembic.ini upgrade head

echo "Starting server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000