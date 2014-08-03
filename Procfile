web:       gunicorn cabot.wsgi:application --config gunicorn.conf
celery:    celery worker -B -A cabot --loglevel=INFO --concurrency=16 -Ofair
