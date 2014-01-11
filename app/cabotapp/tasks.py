import os
import os.path
import sys
import random
import logging
from itertools import chain

from celery import Celery
from celery._state import set_default_app
from celery.task import task

from django.conf import settings
from django.utils import timezone


# Add the root to the python path
root = os.path.abspath(os.path.join(settings.PROJECT_ROOT, '../'))
sys.path.append(root)

celery = Celery(__name__)
celery.config_from_object(settings)

# Celery should set this app as the default, however the 'celery.current_app'
# api uses threadlocals, so code running in different threads/greenlets uses
# the fallback default instead of this app when no app is specified. This
# causes confusing connection errors when celery tries to connect to a
# non-existent rabbitmq server. It seems to happen mostly when using the
# 'celery.canvas' api. To get around this, we use the internal 'celery._state'
# api to force our app to be the default.
set_default_app(celery)
logger = logging.getLogger(__name__)


@task(ignore_result=True)
def run_status_check(check_or_id):
  from .models import StatusCheck
  if not isinstance(check_or_id, StatusCheck):
    check = StatusCheck.objects.get(id=check_or_id)
  else:
    check = check_or_id
  # This will call the subclass method
  check.run()


@task(ignore_result=True)
def run_all_checks():
  from .models import StatusCheck
  from datetime import timedelta, datetime
  checks = StatusCheck.objects.all()
  seconds = range(60)
  for check in checks:
    if check.last_run:
      next_schedule = check.last_run + timedelta(minutes=check.frequency)
    if (not check.last_run) or timezone.now() > next_schedule:
      delay = random.choice(seconds)
      logger.debug('Scheduling task for %s seconds from now' % delay)
      run_status_check.apply_async((check.id,), countdown=delay)


@task(ignore_result=True)
def update_services(ignore_result=True):
  from .models import Service
  for service in Service.objects.all():
    update_service.delay(service.id)


@task(ignore_result=True)
def update_service(service_or_id):
  from .models import Service
  if not isinstance(service_or_id, Service):
    service = Service.objects.get(id=service_or_id)
  else:
    service = service_or_id
  service.update_status()


@task(ignore_result=True)
def update_shifts(ignore_result=True):
  from .models import update_shifts as _update_shifts
  _update_shifts()


