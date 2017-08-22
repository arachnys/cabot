import os
from datetime import timedelta
from kombu import Exchange, Queue
from cabot.metricsapp.defs import GRAFANA_SYNC_TIMEDELTA_MINUTES

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

TIME_MINUTE_IN_SECONDS = 60
TIME_HALF_HOUR_IN_SECONDS = 30 * TIME_MINUTE_IN_SECONDS
TIME_DAY_IN_SECONDS = 24 * 60 * TIME_MINUTE_IN_SECONDS

CELERYBEAT_SCHEDULE = {
    'run-all-checks': {
        'task': 'cabot.cabotapp.tasks.run_all_checks',
        'schedule': timedelta(seconds=TIME_MINUTE_IN_SECONDS),
    },
    'update-shifts': {
        'task': 'cabot.cabotapp.tasks.update_shifts',
        'schedule': timedelta(seconds=TIME_HALF_HOUR_IN_SECONDS),
    },
    'clean-db': {
        'task': 'cabot.cabotapp.tasks.clean_db',
        'schedule': timedelta(seconds=TIME_DAY_IN_SECONDS),
    },
    'sync-all-grafana-checks': {
        'task': 'cabot.metricsapp.tasks.sync_all_grafana_checks',
        'schedule': timedelta(seconds=GRAFANA_SYNC_TIMEDELTA_MINUTES * TIME_MINUTE_IN_SECONDS)
    },
}

CELERY_QUEUES = (
    Queue('checks', Exchange('checks', type='direct'), routing_key='checks'),
    Queue('service', Exchange('service', type='direct'), routing_key='service'),
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
    'cabot.metricsapp.tasks.sync_all_grafana_checks': {
        'queue': 'batch',
        'routing_key': 'batch',
    },
    'cabot.metricsapp.tasks.sync_grafana_check': {
        'queue': 'batch',
        'routing_key': 'batch',
    },
    'cabot.metricsapp.tasks.send_grafana_sync_email': {
        'queue': 'batch',
        'routing_key': 'batch'
    }
}

CELERY_TIMEZONE = 'UTC'

CELERY_RATE_LIMIT = os.environ.get('CELERY_RATE_LIMIT')
if CELERY_RATE_LIMIT:
    CELERY_ANNOTATIONS = {"*": {"rate_limit": CELERY_RATE_LIMIT}}
