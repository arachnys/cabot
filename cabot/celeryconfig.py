import os
from datetime import timedelta

BROKER_URL = os.environ['CELERY_BROKER_URL']
CELERY_IMPORTS = ('cabot.cabotapp.tasks', )
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']

CELERYBEAT_SCHEDULE = {
    'run-all-checks': {
        'task': 'cabot.cabotapp.tasks.run_all_checks',
        'schedule': timedelta(seconds=60),
    },
    'update-shifts': {
        'task': 'cabot.cabotapp.tasks.update_shifts',
        'schedule': timedelta(seconds=1800),
    },
    'clean-db': {
        'task': 'app.cabotapp.tasks.clean_db',
        'schedule': timedelta(seconds=60*60*24),
    },
}

CELERY_TIMEZONE = 'UTC'
