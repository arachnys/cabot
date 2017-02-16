import os
from datetime import timedelta
from kombu import Exchange, Queue

BROKER_URL = os.environ['CELERY_BROKER_URL']
CELERY_IMPORTS = (
    'cabot.cabotapp.tasks',
    'cabot.cabotapp.monitor',
)
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
CELERYD_TASK_SOFT_TIME_LIMIT = 120
CELERYD_TASK_TIME_LIMIT = 240

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
    Queue('checks', Exchange('checks', type='direct'), routing_key='checks'),
    Queue('service', Exchange('service', type='direct'), routing_key='service'),
    Queue('instance', Exchange('instance', type='direct'), routing_key='instance'),
    Queue('batch', Exchange('batch', type='direct'), routing_key='batch'),
    Queue('maintenance', Exchange('maintenance', type='direct'), routing_key='maintenance'),
)

CELERY_ROUTES = {
    'cabot.cabotapp.tasks.run_all_checks': {
        'queue': 'checks',
        'routing_key': 'checks',
    },
    'cabot.cabotapp.tasks.run_status_check': {
        'queue': 'checks',
        'routing_key': 'checks',
    },
    'cabot.cabotapp.tasks.update_service': {
        'queue': 'service',
        'routing_key': 'service',
    },
    'cabot.cabotapp.tasks.update_instance': {
        'queue': 'instance',
        'routing_key': 'instance',
    },
    'cabot.cabotapp.tasks.update_shifts': {
        'queue': 'batch',
        'routing_key': 'batch',
    },
    'cabot.cabotapp.tasks.reset_shifts': {
        'queue': 'batch',
        'routing_key': 'batch',
    },
    'cabot.cabotapp.tasks.clean_db': {
        'queue': 'maintenance',
        'routing_key': 'maintenance',
    },
}

CELERY_TIMEZONE = 'UTC'

CELERY_RATE_LIMIT = os.environ.get('CELERY_RATE_LIMIT')
if CELERY_RATE_LIMIT:
    CELERY_ANNOTATIONS = {"*": {"rate_limit": CELERY_RATE_LIMIT}}
