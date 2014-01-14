from datetime import datetime
from os import environ as env

from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone
import requests

logger = get_task_logger(__name__)

auth = (settings.JENKINS_USER, settings.JENKINS_PASS)


def get_jenkins_url(jobname):
  return settings.JENKINS_API + 'job/%s/api/json' % jobname


def get_job_status(jobname):
  ret = {
    'active': True,
    'succeeded': False,
    'blocked_build_time': None
  }
  endpoint = get_jenkins_url(jobname)
  resp = requests.get(endpoint, auth=auth, verify=True)
  resp.raise_for_status()
  status = resp.json
  if status['color'].startswith('blue'):
    ret['active'] = True
    ret['succeeded'] = True
  elif status['color'] == 'disabled':
    ret['active'] = False
    ret['succeeded'] = False
  if status['queueItem'] and status['queueItem']['blocked']:
    time_blocked_since = datetime.utcfromtimestamp(float(status['queueItem']['inQueueSince'])/1000).replace(tzinfo=timezone.utc)
    ret['time_blocked'] = timezone.now() - time_blocked_since
  return ret
