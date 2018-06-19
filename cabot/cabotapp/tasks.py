from datetime import timedelta
import logging

from celery import Celery
from celery._state import set_default_app
from celery.task import task

from cabot.celery.celery_queue_config import STATUS_CHECK_TO_QUEUE

from django.conf import settings
from django.utils import timezone

from cabot.cabotapp import models
from cabot.metricsapp.models import MetricsStatusCheckBase


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


def _classify_status_check(pk):
    """
    Maps the check to either normal or high priority based on the dict
      cabot.celery.celery_queue_config.STATUS_CHECK_TO_QUEUE
    """
    check = models.StatusCheck.objects.get(pk=pk)

    # If the status check we are running is an instance of MetricsStatusCheckBase
    # (i.e. Grafana/Elasticsearch), then StatusCheck.importance is determined by
    # the type of failure: If the 'high_alert_value' is set and the check fails,
    # the importance is set to ERROR or CRITICAL. However, if this value is null
    # or does not fail, and 'warning_value' is not null and fails instead, then
    # the importance is set to WARNING. As such, we run all importance levels of
    # MetricsStatusCheckBase based on their maximum importance.
    if not isinstance(check, MetricsStatusCheckBase):
        check_queue = STATUS_CHECK_TO_QUEUE[check.check_category][check.importance]
    else:
        if check.high_alert_value is None:
            check_queue = STATUS_CHECK_TO_QUEUE[check.check_category][models.CheckGroupMixin.WARNING_STATUS]
        else:
            check_queue = STATUS_CHECK_TO_QUEUE[check.check_category][check.high_alert_importance]

    return check_queue


@task(ignore_result=True)
def run_status_check(pk):
    check = models.StatusCheck.objects.get(pk=pk)
    check.run()


@task(ignore_result=True)
def run_all_checks():
    checks = models.StatusCheck.objects.filter(active=True).all()
    for check in checks:
        if check.should_run():
            check_queue = _classify_status_check(check.pk)
            run_status_check.apply_async((check.pk,), queue=check_queue)


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
