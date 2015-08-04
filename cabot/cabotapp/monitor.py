from celery.signals import task_success, task_failure
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

try:
    from boto.ec2 import cloudwatch

    if not settings.AWS_CLOUDWATCH_SYNC:
        CONNECTION = None
    else:
        region = settings.AWS_CLOUDWATCH_REGION
        access_key = settings.AWS_CLOUDWATCH_ACCESS_KEY
        secret_key = settings.AWS_CLOUDWATCH_SECRET_KEY

        NAMESPACE = settings.AWS_CLOUDWATCH_NAMESPACE
        PREFIX = settings.AWS_CLOUDWATCH_PREFIX
        CONNECTION = cloudwatch.connect_to_region(
            region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

except ImportError:
    NAMESPACE = None
    PREFIX = None
    CONNECTION = None


try:
    import boto.utils
    _instance = boto.utils.get_instance_metadata()
    DIMENSIONS = {
        'instance-id': _instance['instance-id'],
    }
except ImportError:
    DIMENSIONS = {}


def _notify_cloudwatch(task_name, state):
    '''
    Update cloudwatch with a metric alert about a task
    '''
    if CONNECTION:
        metric = '%s.%s.%s' % (PREFIX, task_name, state)
        try:
            CONNECTION.put_metric_data(NAMESPACE, metric, 1,
                                       dimensions=DIMENSIONS)
        except:
            logger.exception('Error sending cloudwatch metric')


@task_success.connect
def notify_success(sender=None, *args, **kwargs):
    '''
    Update cloudwatch about a task success
    '''
    _notify_cloudwatch(sender, 'success')


@task_failure.connect
def notify_failure(sender=None, *args, **kwargs):
    '''
    Update cloudwatch about a task failure
    '''
    _notify_cloudwatch(sender, 'failure')
