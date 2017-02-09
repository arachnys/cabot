web:       gunicorn cabot.wsgi:application --config gunicorn.conf
celery:    celery worker -A cabot --loglevel=INFO --concurrency=16 -Ofair
beat:      celery beat -A cabot --loglevel=INFO
