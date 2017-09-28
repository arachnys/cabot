#!/bin/bash
set -e

function wait_for_broker {
  set +e
  for try in {1..60} ;  do
    python -c "from kombu import Connection; x=Connection('$CELERY_BROKER_URL', timeout=1); x.connect()" && break
    echo "Waiting for celery broker to respond..."
    sleep 1
  done
}

function wait_for_database {
  set +e
  for try in {1..60} ; do
    python -c "from django.db import connection; connection.connect()" && break
    echo "Waiting for database to respond..."
    sleep 1
  done
}

function wait_for_migrations {
  set +e
  for try in {1..60} ; do
    # Kind of ugly but not sure if there's another way to determine if migrations haven't run.
    # showmigrations -p returns a checkbox list of migrations, empty checkboxes mean they haven't been run
    python manage.py showmigrations -p | grep "\[ \]" &> /dev/null || break
    echo "Waiting for database migrations to be run..."
    sleep 1
  done
}


wait_for_broker
wait_for_database

if [ -z "$SKIP_INIT" ]; then
  /code/bin/build-app
fi

if [ -n "$WAIT_FOR_MIGRATIONS" ]; then
  wait_for_migrations
fi

exec "$@"
