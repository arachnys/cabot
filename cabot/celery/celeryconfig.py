import os
from datetime import timedelta
from kombu import Exchange, Queue
from cabot.celery import defs

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
        'schedule': timedelta(seconds=defs.RUN_ALL_CHECKS_FREQUENCY),
    },
    'update-shifts': {
        'task': 'cabot.cabotapp.tasks.update_shifts',
        'schedule': timedelta(seconds=defs.UPDATE_SHIFTS_FREQUENCY),
    },
    'clean-db': {
        'task': 'cabot.cabotapp.tasks.clean_db',
        'schedule': timedelta(seconds=defs.CLEAN_DB_FREQUENCY),
    },
    'sync-all-grafana-checks': {
        'task': 'cabot.metricsapp.tasks.sync_all_grafana_checks',
        'schedule': timedelta(seconds=defs.SYNC_ALL_GRAFANA_CHECKS_FREQUENCY)
    },
}

CELERY_QUEUES = (
    Queue('normal_checks', Exchange('normal_checks', type='direct'), routing_key='normal_checks'),
    Queue('critical_checks', Exchange('critical_checks', type='direct'), routing_key='critical_checks'),
    Queue('service', Exchange('service', type='direct'), routing_key='service'),
    Queue('batch', Exchange('batch', type='direct'), routing_key='batch'),
    Queue('maintenance', Exchange('maintenance', type='direct'), routing_key='maintenance'),
)

CELERY_ROUTES = {
    'cabot.cabotapp.tasks.run_all_checks': {
        'queue': 'normal_checks',
        'routing_key': 'normal_checks',
    },
    'cabot.cabotapp.tasks.run_status_check': {
        'queue': 'normal_checks',
        'routing_key': 'normal_checks',
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
