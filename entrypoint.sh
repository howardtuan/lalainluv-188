#!/bin/sh
set -eu
python manage.py migrate --noinput
python manage.py sync_admin
python manage.py collectstatic --noinput
if [ "${SEED_DEMO:-False}" = "True" ]; then
    python manage.py seed_demo
    python manage.py seed_banners
fi
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8080}" --workers 3 --threads 2 --worker-class gthread --access-logfile - --error-logfile - --timeout 60
