#!/usr/bin/env bash
set -euo pipefail
export DJANGO_SETTINGS_MODULE=config.settings
export DEBUG=False
export RAILWAY_DEPLOYMENT=True
export PROMETHEUS_EXPORT_MIGRATIONS=False
python manage.py check --deploy --fail-level ERROR
python manage.py migrate --noinput
python manage.py createcachetable
python manage.py bootstrap_platform_owner
python manage.py collectstatic --clear --noinput
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 1 --threads 2 --timeout 120 --access-logfile - --error-logfile -
