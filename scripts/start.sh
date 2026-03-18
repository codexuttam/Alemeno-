#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "Building and starting services..."
docker compose build
docker compose up -d

echo "Running migrations..."
docker compose exec web python manage.py migrate --noinput

echo "Triggering ingestion task (background)..."
docker compose exec web python manage.py ingest_excel

echo "Done. To follow logs run: make logs"
