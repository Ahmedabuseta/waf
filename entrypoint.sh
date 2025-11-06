#!/usr/bin/env sh
set -e

# Defaults
: "${DJANGO_SETTINGS_MODULE:=waf_app.settings}"
: "${GUNICORN_WORKERS:=3}"
: "${GUNICORN_BIND:=0.0.0.0:8000}"

echo "[entrypoint] Using settings: ${DJANGO_SETTINGS_MODULE}"

# Collect static and migrate DB
python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

echo "[entrypoint] Starting Gunicorn on ${GUNICORN_BIND} with ${GUNICORN_WORKERS} workers"
exec gunicorn waf_app.wsgi:application \
  --workers "${GUNICORN_WORKERS}" \
  --bind "${GUNICORN_BIND}" \
  --timeout 60 \
  --log-level info \
  --access-logfile '-' \
  --error-logfile '-'


