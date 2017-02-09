import os
from datetime import timedelta
from kombu import Queue

BROKER_URL = os.environ['CELERY_BROKER_URL']
CELERY_IMPORTS = (
    'cabot.cabotapp.tasks',
    'cabot.cabotapp.monitor',
)
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
CELERYD_TASK_SOFT_TIME_LIMIT = 60
CELERYD_TASK_TIME_LIMIT = 70

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
        'task': 'cabot.cabotapp.tasks.clean_db',
        'schedule': timedelta(seconds=60*60*24),
    },
}

CELERY_QUEUES = (
    Queue('checks'),
    Queue('service'),
    Queue('instance'),
    Queue('batch'),
    Queue('maintenance'),
)

CELERY_ROUTES = {
    'cabot.cabotapp.tasks.run_all_checks': {
        'queue': 'checks',
    },
    'cabot.cabotapp.tasks.run_status_check': {
        'queue': 'checks'
    },
    'cabot.cabotapp.tasks.update_service': {
        'queue': 'service'
    },
    'cabot.cabotapp.tasks.update_instance': {
        'queue': 'instance'
    },
    'cabot.cabotapp.tasks.update_shifts': {
        'queue': 'batch'
    },
    'cabot.cabotapp.tasks.clean_db': {
        'queue': 'maintenance'
    },
}

CELERY_TIMEZONE = 'UTC'

CELERY_RATE_LIMIT = os.environ.get('CELERY_RATE_LIMIT')
if CELERY_RATE_LIMIT:
    CELERY_ANNOTATIONS = {"*": {"rate_limit": CELERY_RATE_LIMIT}}
