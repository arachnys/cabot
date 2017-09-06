from datetime import datetime

from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone
from jenkinsapi.custom_exceptions import UnknownJob
from jenkinsapi.jenkins import Jenkins

logger = get_task_logger(__name__)

JENKINS_CLIENT = None


def _get_jenkins_client(jenkins_config):
    global JENKINS_CLIENT
    if JENKINS_CLIENT is None:
        JENKINS_CLIENT = Jenkins(jenkins_config.jenkins_api,
                                 username=jenkins_config.jenkins_user,
                                 password=jenkins_config.jenkins_pass,
                                 lazy=True)
    return JENKINS_CLIENT

def get_job_status(jenkins_config, jobname):
    ret = {
        'active': None,
        'succeeded': None,
        'job_number': None,
        'blocked_build_time': None,
    }
    client = _get_jenkins_client(jenkins_config)
    try:
        job = client.get_job(jobname)
        last_build = job.get_last_completed_build()

        ret['status_code'] = 200
        ret['job_number'] = last_build.get_number()
        ret['active'] = job.is_enabled()
        ret['succeeded'] = job.is_enabled() and last_build.is_good()

        if job.is_queued():
            in_queued_since = job._data['queueItem']['inQueueSince']  # job.get_queue_item() crashes
            time_blocked_since = datetime.utcfromtimestamp(
                float(in_queued_since) / 1000).replace(tzinfo=timezone.utc)
            ret['blocked_build_time'] = (timezone.now() - time_blocked_since).total_seconds()
            ret['queued_job_number'] = job.get_last_buildnumber()
        return ret
    except UnknownJob:
        ret['status_code'] = 404
        return ret
