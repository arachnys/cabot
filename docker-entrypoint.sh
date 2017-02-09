#!/bin/bash
set -e
set -o allexport

function wait_for_broker {(
  set +e
  for try in {1..60} ;  do
    python -c "from kombu import Connection; x=Connection('$CELERY_BROKER_URL', timeout=1); x.connect()" &> /dev/null && break
    echo "Waiting for celery broker to respond..."
    sleep 1
  done
)}

function wait_for_database {(
  set +e
  for try in {1..60} ; do
    python -c "from django.db import connection; connection.connect()" &> /dev/null && break
    echo "Waiting for database to respond..."
    sleep 1
  done
)}


wait_for_broker
wait_for_database

if [ -z "$SKIP_INIT" ]; then
  /code/bin/build-app
fi

exec "$@"
