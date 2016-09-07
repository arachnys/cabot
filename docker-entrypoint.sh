#!/bin/bash

set -e

# first check if we're passing flags, if so
# prepend with sentry
if [ "${1:0:1}" = '-' ]; then
	set -- python manage.py "$@"
fi

case "$1" in
"web")
	set -- gunicorn cabot.wsgi:application --config gunicorn.conf
	;;
"beatworker")
    set -- celery worker -B -A cabot --loglevel=INFO --concurrency=16 -Ofair
    ;;
"worker")
    set -- celery worker -A cabot --loglevel=INFO --concurrency=16 -Ofair
    ;;
esac

exec "$@"