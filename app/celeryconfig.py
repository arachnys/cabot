import os
from datetime import timedelta

BROKER_URL = os.environ['CELERY_BROKER_URL']
CELERY_IMPORTS = ('app.cabotapp.tasks', )
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']

CELERYBEAT_SCHEDULE = {
    'run-all-checks': {
        'task': 'app.cabotapp.tasks.run_all_checks',
        'schedule': timedelta(seconds=60),
    },
    'update-shifts': {
        'task': 'app.cabotapp.tasks.update_shifts',
        'schedule': timedelta(seconds=1800),
    },
}

CELERY_TIMEZONE = 'UTC'