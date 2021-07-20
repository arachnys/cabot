from __future__ import absolute_import

import os
from datetime import timedelta

from django.conf import settings
from celery import Celery

from .config import config_charge

config_charge()

os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'cabot.settings')

app = Celery('cabot')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
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
        'schedule': timedelta(seconds=120),
    },
}