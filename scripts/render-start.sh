#!/usr/bin/env bash
set -euo pipefail
python manage.py migrate --noinput
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-10000}" --workers 1 --threads 2 --timeout 120 --access-logfile - --error-logfile -
