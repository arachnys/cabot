from datetime import timedelta
import random
import logging

from celery import Celery
from celery._state import set_default_app
from celery.task import task

from django.conf import settings
from django.db import transaction
from django.utils import timezone

import models

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
    if not isinstance(check_or_id, models.StatusCheck):
        check = models.StatusCheck.objects.get(id=check_or_id)
    else:
        check = check_or_id
    # This will call the subclass method
    check.run()


@task(ignore_result=True)
def run_all_checks():
    checks = models.StatusCheck.objects.filter(active=True).all()
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
    # Avoid importerrors and the like from legacy scheduling
    return


@task(ignore_result=True)
def update_service(service_or_id):
    if not isinstance(service_or_id, models.Service):
        service = models.Service.objects.get(id=service_or_id)
    else:
        service = service_or_id
    service.update_status()


@task(ignore_result=True)
def update_shifts():
    schedules = models.Schedule.objects.all()
    for schedule in schedules:
        models.update_shifts(schedule)


@task(ignore_result=True)
def reset_shifts(schedule_id):
    try:
        schedule = models.Schedule.objects.get(id=schedule_id)
        models.delete_shifts(schedule)
        models.update_shifts(schedule)
    except Exception as e:
        logger.exception('Error when resetting shifts: {}'.format(e))


@task(ignore_result=True)
def clean_db(days_to_retain=60):
    """
    Clean up database otherwise it gets overwhelmed with StatusCheckResults.

    To loop over undeleted results, spawn new tasks to make sure
    db connection closed etc
    """

    to_discard_results = models.StatusCheckResult.objects.filter(
        time__lte=timezone.now()-timedelta(days=days_to_retain))
    to_discard_snapshots = models.ServiceStatusSnapshot.objects.filter(
        time__lte=timezone.now()-timedelta(days=days_to_retain))

    result_ids = to_discard_results.values_list('id', flat=True)[:100]
    snapshot_ids = to_discard_snapshots.values_list('id', flat=True)[:100]

    if not result_ids:
        logger.info('Completed deleting StatusCheckResult objects')
    if not snapshot_ids:
        logger.info('Completed deleting ServiceStatusSnapshot objects')
    if (not snapshot_ids) and (not result_ids):
        return

    logger.info('Processing %s StatusCheckResult objects' % len(result_ids))
    logger.info('Processing %s ServiceStatusSnapshot objects' %
                len(snapshot_ids))

    models.StatusCheckResult.objects.filter(id__in=result_ids).delete()
    models.ServiceStatusSnapshot.objects.filter(id__in=snapshot_ids).delete()

    clean_db.apply_async(kwargs={'days_to_retain': days_to_retain},
                         countdown=3)
