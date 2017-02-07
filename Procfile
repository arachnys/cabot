web:       gunicorn cabot.wsgi:application --config gunicorn.conf --log-file -
celery:    celery worker -B -A cabot --loglevel=INFO --concurrency=16 -Ofair 2>&1
