import os
from datetime import timedelta
from cabot.settings_utils import environ_get_list

BROKER_URL = environ_get_list(['CELERY_BROKER_URL', 'CACHE_URL'])
# Set environment variable if you want to run tests without a redis instance
CELERY_ALWAYS_EAGER = os.environ.get('CELERY_ALWAYS_EAGER', False)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', None)
CELERY_IMPORTS = ('cabot.cabotapp.tasks', )
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
CELERYD_TASK_SOFT_TIME_LIMIT = 120
CELERYD_TASK_TIME_LIMIT = 150

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
        'schedule': timedelta(seconds=60 * 60 * 24),
    },
}

CELERY_TIMEZONE = 'UTC'
