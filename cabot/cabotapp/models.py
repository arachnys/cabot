from django.db import models
from django.conf import settings
from polymorphic import PolymorphicModel
from django.contrib.auth.models import User
from celery.exceptions import SoftTimeLimitExceeded

from .jenkins import get_job_status
from .alert import (send_alert, AlertPluginUserData)
from .influx import parse_metric
from .tasks import update_service, update_instance
from cabot.cabotapp.models_plugins import HipchatInstance

from collections import defaultdict
from datetime import timedelta
from django.utils import timezone
from icalendar import Calendar


import json
import re
import time
import subprocess
import yaml

import requests
from celery.utils.log import get_task_logger

RAW_DATA_LIMIT = 500000

logger = get_task_logger(__name__)

CHECK_TYPES = (
    ('>', 'Greater than'),
    ('>=', 'Greater than or equal'),
    ('<', 'Less than'),
    ('<=', 'Less than or equal'),
    ('==', 'Equal to'),
)


def serialize_recent_results(recent_results):
    if not recent_results:
        return ''

    def result_to_value(result):
        if result.succeeded:
            return '1'
        else:
            return '-1'
    vals = [result_to_value(r) for r in recent_results]
    vals.reverse()
    return ','.join(vals)


def get_success_with_retries(recent_results, retries=0):
    """
    `retries` are the number of previous failures we need (not including this)
    to mark a search as passing or failing
    Returns:
      True if passing given number of retries
      False if failing
    """
    if not recent_results:
        return True
    retry_window = recent_results[:retries + 1]
    for r in retry_window:
        if r.succeeded:
            return True
    return False


class CheckGroupMixin(models.Model):

    class Meta:
        abstract = True

    PASSING_STATUS = 'PASSING'
    WARNING_STATUS = 'WARNING'
    ERROR_STATUS = 'ERROR'
    CRITICAL_STATUS = 'CRITICAL'

    CALCULATED_PASSING_STATUS = 'passing'
    CALCULATED_INTERMITTENT_STATUS = 'intermittent'
    CALCULATED_FAILING_STATUS = 'failing'

    STATUSES = (
        (CALCULATED_PASSING_STATUS, CALCULATED_PASSING_STATUS),
        (CALCULATED_INTERMITTENT_STATUS, CALCULATED_INTERMITTENT_STATUS),
        (CALCULATED_FAILING_STATUS, CALCULATED_FAILING_STATUS),
    )

    IMPORTANCES = (
        (WARNING_STATUS, 'Warning'),
        (ERROR_STATUS, 'Error'),
        (CRITICAL_STATUS, 'Critical'),
    )

    name = models.TextField()

    users_to_notify = models.ManyToManyField(
        User,
        blank=True,
        help_text='Users who should receive alerts.',
    )
    schedules = models.ManyToManyField(
        'Schedule',
        blank=True,
        null=True,
        help_text='Oncall schedule to be alerted.'
    )
    alerts_enabled = models.BooleanField(
        default=True,
        help_text='Alert when this service is not healthy.',
    )
    status_checks = models.ManyToManyField(
        'StatusCheck',
        blank=True,
        help_text='Checks used to calculate service status.',
    )
    last_alert_sent = models.DateTimeField(
        null=True,
        blank=True,
    )

    alerts = models.ManyToManyField(
        'AlertPlugin',
        blank=True,
        help_text='Alerts channels through which you wish to be notified'
    )

    email_alert = models.BooleanField(default=False)
    hipchat_alert = models.BooleanField(default=True)
    sms_alert = models.BooleanField(default=False)
    telephone_alert = models.BooleanField(
        default=False,
        help_text='Must be enabled, and check importance set to Critical, to receive telephone alerts.',
    )
    overall_status = models.TextField(default=PASSING_STATUS)
    old_overall_status = models.TextField(default=PASSING_STATUS)
    hackpad_id = models.TextField(
        null=True,
        blank=True,
        verbose_name='Recovery instructions',
        help_text='Gist, Hackpad or Refheap js embed with recovery instructions e.g. '
                  'https://you.hackpad.com/some_document.js'
    )
    hipchat_instance = models.ForeignKey(
        'HipchatInstance',
        null=True,
        blank=True,
        help_text='Hipchat instance to send Hipchat alerts to (can be none if Hipchat alerts disabled).'
    )
    hipchat_room_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='Id of the Hipchat room to be alerted for this service (can be none).'
    )

    def __unicode__(self):
        return self.name

    def most_severe(self, check_list):
        failures = [c.importance for c in check_list]
        if self.CRITICAL_STATUS in failures:
            return self.CRITICAL_STATUS
        if self.ERROR_STATUS in failures:
            return self.ERROR_STATUS
        if self.WARNING_STATUS in failures:
            return self.WARNING_STATUS
        return self.PASSING_STATUS

    @property
    def is_critical(self):
        """
        Break out separately because it's a bit of a pain to
        get wrong.
        """
        if self.old_overall_status != self.CRITICAL_STATUS and self.overall_status == self.CRITICAL_STATUS:
            return True
        return False

    def alert(self):
        if not self.alerts_enabled:
            return
        if self.overall_status != self.PASSING_STATUS:
            # We want to alert if the status changes no matter what
            if self.overall_status == self.old_overall_status:
                # Don't alert every time if status hasn't changed
                if self.overall_status == self.WARNING_STATUS:
                    if self.last_alert_sent and (timezone.now() - timedelta(minutes=settings.NOTIFICATION_INTERVAL)) \
                            < self.last_alert_sent:
                        return
                elif self.overall_status in (self.CRITICAL_STATUS, self.ERROR_STATUS):
                    if self.last_alert_sent and (timezone.now() - timedelta(minutes=settings.ALERT_INTERVAL)) \
                            < self.last_alert_sent:
                        return
            self.last_alert_sent = timezone.now()
        else:
            # We don't count "back to normal" as an alert
            self.last_alert_sent = None
        self.save()
        self.snapshot.did_send_alert = True
        self.snapshot.save()

        schedules = self.schedules.all()

        if not schedules:
            send_alert(self)

        for schedule in schedules:
            send_alert(self, duty_officers=get_duty_officers(schedule),
                       fallback_officers=get_fallback_officers(schedule))

    @property
    def recent_snapshots(self):
        snapshots = self.snapshots.filter(
            time__gt=(timezone.now() - timedelta(minutes=60 * 24)))
        snapshots = list(snapshots.values())
        for s in snapshots:
            s['time'] = time.mktime(s['time'].timetuple())
        return snapshots

    def graphite_status_checks(self):
        return self.status_checks.filter(polymorphic_ctype__model='graphitestatuscheck')

    def http_status_checks(self):
        return self.status_checks.filter(polymorphic_ctype__model='httpstatuscheck')

    def jenkins_status_checks(self):
        return self.status_checks.filter(polymorphic_ctype__model='jenkinsstatuscheck')

    def elasticsearch_status_checks(self):
        return self.status_checks.filter(polymorphic_ctype__model='elasticsearchstatuscheck')

    def active_graphite_status_checks(self):
        return self.graphite_status_checks().filter(active=True)

    def active_http_status_checks(self):
        return self.http_status_checks().filter(active=True)

    def active_jenkins_status_checks(self):
        return self.jenkins_status_checks().filter(active=True)

    def active_status_checks(self):
        return self.status_checks.filter(active=True)

    def inactive_status_checks(self):
        return self.status_checks.filter(active=False)

    def all_passing_checks(self):
        return self.active_status_checks().filter(calculated_status=self.CALCULATED_PASSING_STATUS)

    def all_failing_checks(self):
        return self.active_status_checks().exclude(calculated_status=self.CALCULATED_PASSING_STATUS)


class Schedule(models.Model):
    name = models.CharField(
        unique=True,
        max_length=50,
        help_text='Display name for the oncall schedule.')
    ical_url = models.TextField(help_text='ical url of the oncall schedule.')
    fallback_officer = models.ForeignKey(
        User,
        blank=True,
        null=True,
        help_text='Fallback officer to alert if the duty officer is unavailable.'
    )

    def get_calendar_data(self):
        """
        Parse icalendar data
        :return: String containing the calendar data
        """
        resp = requests.get(self.ical_url)
        return Calendar.from_ical(resp.content)

    def __unicode__(self):
        return self.name


class Service(CheckGroupMixin):

    def update_status(self):
        self.old_overall_status = self.overall_status
        # Only active checks feed into our calculation
        status_checks_failed_count = self.all_failing_checks().count()
        self.overall_status = self.most_severe(self.all_failing_checks())
        self.snapshot = ServiceStatusSnapshot(
            service=self,
            num_checks_active=self.active_status_checks().count(),
            num_checks_passing=self.active_status_checks(
            ).count() - status_checks_failed_count,
            num_checks_failing=status_checks_failed_count,
            overall_status=self.overall_status,
            time=timezone.now(),
        )
        self.snapshot.save()
        self.save()
        if not (self.overall_status == Service.PASSING_STATUS and self.old_overall_status == Service.PASSING_STATUS):
            self.alert()

    instances = models.ManyToManyField(
        'Instance',
        blank=True,
        help_text='Instances this service is running on.',
    )

    url = models.TextField(
        blank=True,
        help_text="URL of service."
    )

    class Meta:
        ordering = ['name']


class Instance(CheckGroupMixin):

    def duplicate(self):
        checks = self.status_checks.all()
        new_instance = self
        new_instance.pk = None
        new_instance.id = None
        new_instance.name = u"Copy of %s" % self.name

        new_instance.save()

        for check in checks:
            check.duplicate(inst_set=(new_instance,), serv_set=())

        return new_instance.pk

    def update_status(self):
        self.old_overall_status = self.overall_status
        # Only active checks feed into our calculation
        status_checks_failed_count = self.all_failing_checks().count()
        self.overall_status = self.most_severe(self.all_failing_checks())
        self.snapshot = InstanceStatusSnapshot(
            instance=self,
            num_checks_active=self.active_status_checks().count(),
            num_checks_passing=self.active_status_checks(
            ).count() - status_checks_failed_count,
            num_checks_failing=status_checks_failed_count,
            overall_status=self.overall_status,
            time=timezone.now(),
        )
        self.snapshot.save()
        self.save()

    class Meta:
        ordering = ['name']

    address = models.TextField(
        blank=True,
        help_text="Address (IP/Hostname) of service."
    )

    def icmp_status_checks(self):
        return self.status_checks.filter(polymorphic_ctype__model='icmpstatuscheck')

    def active_icmp_status_checks(self):
        return self.icmp_status_checks().filter(active=True)

    def delete(self, *args, **kwargs):
        self.icmp_status_checks().delete()
        return super(Instance, self).delete(*args, **kwargs)


class Snapshot(models.Model):

    class Meta:
        abstract = True

    time = models.DateTimeField(db_index=True)
    num_checks_active = models.IntegerField(default=0)
    num_checks_passing = models.IntegerField(default=0)
    num_checks_failing = models.IntegerField(default=0)
    overall_status = models.TextField(default=Service.PASSING_STATUS)
    did_send_alert = models.IntegerField(default=False)


class ServiceStatusSnapshot(Snapshot):
    service = models.ForeignKey(Service, related_name='snapshots')

    def __unicode__(self):
        return u"%s: %s" % (self.service.name, self.overall_status)


class InstanceStatusSnapshot(Snapshot):
    instance = models.ForeignKey(Instance, related_name='snapshots')

    def __unicode__(self):
        return u"%s: %s" % (self.instance.name, self.overall_status)


class StatusCheck(PolymorphicModel):

    """
    Base class for polymorphic models. We're going to use
    proxy models for inheriting because it makes life much simpler,
    but this allows us to stick different methods etc on subclasses.

    You can work out what (sub)class a model is an instance of by accessing `instance.polymorphic_ctype.model`

    We are using django-polymorphic for polymorphism
    """

    # Common attributes to all
    name = models.TextField()
    active = models.BooleanField(
        default=True,
        help_text='If not active, check will not be used to calculate service status and will not trigger alerts.',
    )
    importance = models.CharField(
        max_length=30,
        choices=Service.IMPORTANCES,
        default=Service.ERROR_STATUS,
        help_text='Severity level of a failure. Critical alerts are for failures you want to wake you up at 2am, '
                  'Errors are things you can sleep through but need to fix in the morning, '
                  'and warnings for less important things.'
    )
    frequency = models.IntegerField(
        default=5,
        help_text='Minutes between each check.',
    )
    retries = models.IntegerField(
        default=0,
        null=True,
        help_text='Number of successive failures permitted before check will be marked as failed. '
                  'Default is 0, i.e. fail on first failure.'
    )
    created_by = models.ForeignKey(User, null=True)
    calculated_status = models.CharField(
        max_length=50, choices=Service.STATUSES, default=Service.CALCULATED_PASSING_STATUS, blank=True)
    last_run = models.DateTimeField(null=True)
    cached_health = models.TextField(editable=False, null=True)

    class Meta(PolymorphicModel.Meta):
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def recent_results(self):
        # Not great to use id but we are getting lockups, possibly because of something to do with index
        # on time_complete
        return StatusCheckResult.objects.filter(check=self).order_by('-id').defer('raw_data')[:10]

    def last_result(self):
        try:
            return StatusCheckResult.objects.filter(check=self).order_by('-id').defer('raw_data')[0]
        except:
            return None

    def run(self):
        start = timezone.now()
        try:
            result = self._run()
        except SoftTimeLimitExceeded as e:
            result = StatusCheckResult(check=self)
            result.error = u'Error in performing check: Celery soft time limit exceeded'
            result.succeeded = False
        except Exception as e:
            result = StatusCheckResult(check=self)
            result.error = u'Error in performing check: %s' % (e,)
            result.succeeded = False
        finish = timezone.now()
        result.time = start
        result.time_complete = finish
        result.save()
        self.last_run = finish
        self.save()

    def _run(self):
        """
        Implement on subclasses. Should return a `CheckResult` instance.
        """
        raise NotImplementedError('Subclasses should implement')

    def save(self, *args, **kwargs):
        if self.last_run:
            recent_results = list(self.recent_results())
            if get_success_with_retries(recent_results, self.retries):
                self.calculated_status = Service.CALCULATED_PASSING_STATUS
            else:
                self.calculated_status = Service.CALCULATED_FAILING_STATUS
            self.cached_health = serialize_recent_results(recent_results)
            try:
                updated = StatusCheck.objects.get(pk=self.pk)
            except StatusCheck.DoesNotExist:
                logger.error('Cannot find myself (check %s) in the database, presumably have been deleted' % self.pk)
                return
        else:
            self.cached_health = ''
            self.calculated_status = Service.CALCULATED_PASSING_STATUS
        ret = super(StatusCheck, self).save(*args, **kwargs)
        self.update_related_services()
        self.update_related_instances()
        return ret

    def duplicate(self, inst_set=(), serv_set=()):
        new_check = self
        new_check.pk = None
        new_check.id = None
        new_check.name = 'Copy of {}'.format(self.name)
        new_check.last_run = None
        new_check.save()
        for linked in list(inst_set) + list(serv_set):
            linked.status_checks.add(new_check)
        return new_check.pk

    def update_related_services(self):
        services = self.service_set.all()
        for service in services:
            update_service.apply_async(args=[service.id])

    def update_related_instances(self):
        instances = self.instance_set.all()
        for instance in instances:
            update_instance.apply_async(args=[instance.id])

    def get_status_image(self):
        """Return a related image for the check (if it exists)"""
        return None

    def get_status_link(self):
        """Return a link with more information about the check"""
        return None


class ICMPStatusCheck(StatusCheck):

    @property
    def check_category(self):
        return "ICMP/Ping Check"

    @property
    def description(self):
        instances = self.instance_set.all()
        if len(instances) > 0:
            return 'ICMP Reply from {}'.format(self.instance_set.all()[0].address)
        return 'ICMP Reply'

    update_url = 'update-icmp-check'

    icon = 'glyphicon glyphicon-transfer'

    def _run(self):
        result = StatusCheckResult(check=self)
        instances = self.instance_set.all()
        target = self.instance_set.get().address

        # We need to read both STDOUT and STDERR because ping can write to both, depending on the kind of error.
        # Thanks a lot, ping.
        ping_process = subprocess.Popen("ping -c 1 " + target,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        shell=True)
        response = ping_process.wait()

        if response == 0:
            result.succeeded = True
        else:
            output = ping_process.stdout.read()
            result.succeeded = False
            result.error = output

        return result


class GraphiteStatusCheck(StatusCheck):
    """
    Uses influx, not graphite
    """

    @property
    def check_category(self):
        return "Metric check"

    @property
    def description(self):
        desc = ['{} {} {}'.format(self.metric[:70], self.check_type, self.value)]
        if self.expected_num_hosts is not None:
            desc.append(' from {} hosts'.format(self.expected_num_hosts))
        return ''.join(desc)

    update_url = 'update-graphite-check'

    icon = 'glyphicon glyphicon-signal'

    metric = models.TextField(
        null=True,
        help_text='fully.qualified.name of the metric you want to watch. '
                  'This can be any valid expression, including wildcards, '
                  'multiple hosts, etc.',
    )
    metric_selector = models.CharField(
        max_length=50,
        null=False,
        default='value',
        help_text='The selector for the metric. '
                  'Can be specified as "value", "mean(value)", '
                  '"percentile(value, 90)" etc.',
    )
    check_type = models.CharField(
        choices=CHECK_TYPES,
        max_length=100,
        null=True,
    )
    value = models.TextField(
        null=True,
        help_text='If this expression evaluates to False, the check will fail (possibly triggering an alert).',
    )
    group_by = models.CharField(
        max_length=50,
        null=False,
        default='',
        help_text='The "group by" clause for the metric. '
                  'Can be specified as "time(1m)", '
                  '"time(2m), host" etc.',
    )
    fill_empty = models.IntegerField(
        default=None,
        null=True,
        blank=True,
        help_text='Fill the sequence with this value, if required.'
    )
    where_clause = models.CharField(
        max_length=256,
        null=False,
        default='',
        blank=True,
        help_text='The "where clause" for selecting the metric'
    )
    expected_num_hosts = models.IntegerField(
        default=0,
        null=True,
        help_text='The minimum number of data series (hosts) you expect to see.',
    )
    expected_num_metrics = models.IntegerField(
        default=0,
        null=True,
        help_text='The minimum number of data series (metrics) you expect to satisfy given condition.',
    )
    interval = models.IntegerField(
        default=5,
        help_text='Time duration (in minutes) for checking metrics'
    )

    def format_error_message(self, failure_value, actual_hosts,
                             actual_metrics, name):
        """
        A summary of why the check is failing for inclusion in short
        alert messages

        Returns something like:
        "5.0 > 4 | 1/2 hosts"
        """
        hosts_string = u''
        if self.expected_num_hosts > 0:
            hosts_string = u' | %s/%s hosts' % (actual_hosts,
                                                self.expected_num_hosts)
            if self.expected_num_hosts > actual_hosts:
                return u'Hosts missing%s' % hosts_string
        if self.expected_num_metrics > 0:
            metrics_string = u'%s | %s/%s metrics' % (name,
                                                      actual_metrics,
                                                      self.expected_num_metrics)
            if self.expected_num_metrics > actual_metrics:
                return u'Metrics condition missed for %s' % metrics_string
        if failure_value is None:
            return "Failed to get metric from Graphite"
        return u"%0.1f %s %0.1f%s" % (
            failure_value,
            self.check_type,
            float(self.value),
            hosts_string
        )

    def _run(self):
        series = parse_metric(self.metric,
                              selector=self.metric_selector,
                              group_by=self.group_by,
                              fill_empty=self.fill_empty,
                              where_clause=self.where_clause,
                              time_delta=self.interval * 6)

        result = StatusCheckResult(
            check=self,
        )

        if series['error']:
            result.succeeded = False
            result.error = 'Error fetching metric from source'
            return result
        else:
            failed = None

        # Add a threshold in the graph
        threshold = None
        if series['raw'] and series['raw'][0]['datapoints']:
            start = series['raw'][0]['datapoints'][0]
            end = series['raw'][0]['datapoints'][-1]
            threshold = dict(target='alert.threshold',
                             datapoints=[(self.value, start[1]),
                                         (self.value, end[1])])

        failure_value = 0
        failed_metric_name = None
        matched_metrics = 0

        # First do some crazy average checks (if we expect more than 1 metric)
        if series['num_series_with_data'] > 0:
            result.average_value = series['average_value']
            if self.check_type == '<':
                failed = not float(series['min']) < float(self.value)
                if failed:
                    failure_value = series['min']
            elif self.check_type == '<=':
                failed = not float(series['min']) <= float(self.value)
                if failed:
                    failure_value = series['min']
            elif self.check_type == '>':
                failed = not float(series['max']) > float(self.value)
                if failed:
                    failure_value = series['max']
            elif self.check_type == '>=':
                failed = not float(series['max']) >= float(self.value)
                if failed:
                    failure_value = series['max']
            elif self.check_type == '==':
                failed = not float(self.value) in series['all_values']
                if failed:
                    failure_value = float(self.value)
            else:
                raise Exception(u'Check type %s not supported' %
                                self.check_type)

        if series['num_series_with_data'] < self.expected_num_hosts:
            failed = True

        reference_point = time.time() - ((self.interval + 2) * 60)

        if self.expected_num_metrics > 0:
            json_series = series['raw']
            logger.info("Processing series " + str(json_series))
            for line in json_series:
                matched_metrics = 0

                for point in line['datapoints']:

                    last_value = point[0]
                    time_stamp = point[1]

                    if time_stamp <= reference_point:
                        logger.debug('Point %s is older than ref ts %d' %
                                     (str(point), reference_point))
                        continue

                    if last_value is not None:
                        if self.check_type == '<':
                            metric_failed = not last_value < float(self.value)
                        elif self.check_type == '<=':
                            metric_failed = not last_value <= float(self.value)
                        elif self.check_type == '>':
                            metric_failed = not last_value > float(self.value)
                        elif self.check_type == '>=':
                            metric_failed = not last_value >= float(self.value)
                        elif self.check_type == '==':
                            metric_failed = not last_value == float(self.value)
                        else:
                            raise Exception(u'Check type %s not supported' %
                                            self.check_type)
                        if metric_failed:
                            failure_value = last_value
                            failed_metric_name = line['target']
                        else:
                            matched_metrics += 1
                            logger.info("Metrics matched: " + str(matched_metrics))
                            logger.info("Required metrics: " + str(self.expected_num_metrics))
                    else:
                        failed = True

                logger.info("Processing series ...")

                if matched_metrics < self.expected_num_metrics:
                    failed = True
                    failure_value = None
                    failed_metric_name = line['target']
                    break
                else:
                    failed = False

        try:
            if threshold is not None:
                series['raw'].append(threshold)
            result.raw_data = json.dumps(series['raw'], indent=2)
        except:
            result.raw_data = series['raw']
        result.succeeded = not failed

        if not result.succeeded:
            result.error = self.format_error_message(
                failure_value,
                series['num_series_with_data'],
                matched_metrics,
                failed_metric_name,
            )

        result.actual_hosts = series['num_series_with_data']
        result.actual_metrics = matched_metrics
        result.failure_value = failure_value
        return result


class InfluxDBStatusCheck(GraphiteStatusCheck):
    """
    Duplicate of GraphiteStatusCheck
    """
    class Meta(GraphiteStatusCheck.Meta):
        pass


class HttpStatusCheck(StatusCheck):

    @property
    def check_category(self):
        return "HTTP check"

    @property
    def description(self):
        desc = ['Status code {} from {}'.format(self.status_code, self.endpoint)]
        if self.text_match:
            desc.append('; match text /{}/'.format(self.text_match))
        return ''.join(desc)

    update_url = 'update-http-check'

    icon = 'glyphicon glyphicon-arrow-up'

    endpoint = models.TextField(
        null=True,
        help_text='HTTP(S) endpoint to poll.',
    )
    username = models.TextField(
        blank=True,
        null=True,
        help_text='Basic auth username.',
    )
    password = models.TextField(
        blank=True,
        null=True,
        help_text='Basic auth password.',
    )
    http_method = models.CharField(
        null=False,
        max_length=10,
        default='GET',
        choices=(('GET', 'GET'), ('POST', 'POST'), ('HEAD', 'HEAD')),
        help_text='The method to use for invocation',
    )
    http_params = models.TextField(
        default=None,
        null=True,
        blank=True,
        help_text='Yaml representation of "header: regex" to send as parameters',
    )
    http_body = models.TextField(
        null=True,
        default=None,
        blank=True,
        help_text='Yaml representation of key: value to send as data'
    )
    allow_http_redirects = models.BooleanField(
        default=True,
        help_text='Indicates if the check should follow an http redirect'
    )
    text_match = models.TextField(
        blank=True,
        null=True,
        help_text='Regex to match against source of page.',
    )
    header_match = models.TextField(
        default=None,
        null=True,
        blank=True,
        help_text='Yaml representation of "header: regex" to match in '
                  'the results',
    )
    timeout = models.IntegerField(
        default=30,
        null=True,
        help_text='Time out after this many seconds.',
    )
    verify_ssl_certificate = models.BooleanField(
        default=True,
        help_text='Set to false to allow not try to verify ssl certificates (default True)',
    )
    status_code = models.TextField(
        default=200,
        null=True,
        help_text='Status code expected from endpoint.'
    )

    def _run(self):
        result = StatusCheckResult(check=self)
        if self.username:
            auth = (self.username, self.password)
        else:
            auth = None

        try:
            http_params = yaml.load(self.http_params)
        except:
            http_params = self.http_params

        try:
            http_body = yaml.load(self.http_body)
        except:
            http_body = self.http_body

        try:
            header_match = yaml.load(self.header_match)
        except:
            header_match = self.header_match

        try:
            resp = requests.request(
                method=self.http_method,
                url=self.endpoint,
                data=http_body,
                params=http_params,
                timeout=self.timeout,
                verify=self.verify_ssl_certificate,
                auth=auth,
                allow_redirects=self.allow_http_redirects
            )
        except requests.RequestException as e:
            result.error = u'Request error occurred: %s' % (e.message,)
            result.succeeded = False
        else:
            result.raw_data = resp.content
            result.succeeded = False

            if self.status_code and resp.status_code != int(self.status_code):
                result.error = u'Wrong code: got %s (expected %s)' % (
                    resp.status_code, int(self.status_code))
                return result

            if self.text_match is not None:
                if not re.search(self.text_match, resp.content):
                    result.error = u'Failed to find match regex /%s/ in response body' % self.text_match
                    return result

            if type(header_match) is dict and header_match:
                for header, match in header_match.iteritems():
                    if header not in resp.headers:
                        result.error = u'Missing response header: %s' % (header)
                        return result

                    value = resp.headers[header]
                    if not re.match(match, value):
                        result.error = u'Mismatch in header: %s / %s' % (header, value)
                        return result

            # Mark it as success. phew!!
            result.succeeded = True

        return result


class JenkinsStatusCheck(StatusCheck):

    @property
    def check_category(self):
        return "Jenkins check"

    @property
    def description(self):
        desc = ['Monitor job {}'.format(self.name)]
        if self.max_queued_build_time is not None:
            desc.append('; no build waiting for > {} minutes'.format(self.max_queued_build_time))
        return ''.join(desc)

    update_url = 'update-jenkins-check'

    icon ='glyphicon glyphicon-ok'

    max_queued_build_time = models.IntegerField(
        null=True,
        blank=True,
        help_text='Alert if build queued for more than this many minutes.',
    )

    @property
    def failing_short_status(self):
        return 'Job failing on Jenkins'

    def _run(self):
        result = StatusCheckResult(check=self)
        try:
            status = get_job_status(self.name)
            active = status['active']
            result.job_number = status['job_number']
            if status['status_code'] == 404:
                result.error = u'Job %s not found on Jenkins' % self.name
                result.succeeded = False
                return result
            elif status['status_code'] > 400:
                # Will fall through to next block
                raise Exception(u'returned %s' % status['status_code'])
        except Exception as e:
            # If something else goes wrong, we will *not* fail - otherwise
            # a lot of services seem to fail all at once.
            # Ugly to do it here but...
            result.error = u'Error fetching from Jenkins - %s' % e.message
            result.succeeded = False
            return result

        if not active:
            # We will fail if the job has been disabled
            result.error = u'Job "%s" disabled on Jenkins' % self.name
            result.succeeded = False
        else:
            if self.max_queued_build_time and status['blocked_build_time']:
                if status['blocked_build_time'] > self.max_queued_build_time * 60:
                    result.succeeded = False
                    result.error = u'Job "%s" has blocked build waiting for %ss (> %sm)' % (
                        self.name,
                        int(status['blocked_build_time']),
                        self.max_queued_build_time,
                    )
                else:
                    result.succeeded = status['succeeded']
            else:
                result.succeeded = status['succeeded']
            if not status['succeeded']:
                if result.error:
                    result.error += u'; Job "%s" failing on Jenkins' % self.name
                else:
                    result.error = u'Job "%s" failing on Jenkins' % self.name
                result.raw_data = status

        return result


class StatusCheckResult(models.Model):

    """
    We use the same StatusCheckResult model for all check types,
    because really they are not so very different.

    Checks don't have to use all the fields, so most should be
    nullable
    """
    check = models.ForeignKey(StatusCheck)
    time = models.DateTimeField(null=False, db_index=True)
    time_complete = models.DateTimeField(null=True, db_index=True)
    raw_data = models.TextField(null=True)
    succeeded = models.BooleanField(default=False)
    error = models.TextField(null=True)

    # Jenkins specific
    job_number = models.PositiveIntegerField(null=True)

    def __unicode__(self):
        return '%s: %s @%s' % (self.status, self.check.name, self.time)

    @property
    def status(self):
        if self.succeeded:
            return 'succeeded'
        else:
            return 'failed'

    @property
    def took(self):
        try:
            return (self.time_complete - self.time).microseconds / 1000
        except:
            return None

    @property
    def short_error(self):
        snippet_len = 30
        if len(self.error) > snippet_len:
            return u"%s..." % self.error[:snippet_len - 3]
        else:
            return self.error

    def save(self, *args, **kwargs):
        if isinstance(self.raw_data, basestring):
            self.raw_data = self.raw_data[:RAW_DATA_LIMIT]
        return super(StatusCheckResult, self).save(*args, **kwargs)


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')

    def user_data(self):
        for user_data_subclass in AlertPluginUserData.__subclasses__():
            user_data = user_data_subclass.objects.get_or_create(user=self, title=user_data_subclass.name)
        return AlertPluginUserData.objects.filter(user=self)

    def __unicode__(self):
        return 'User profile: %s' % self.user.username

    @property
    def prefixed_mobile_number(self):
        return '+%s' % self.mobile_number

    mobile_number = models.CharField(max_length=20, blank=True, default='')
    hipchat_alias = models.CharField(max_length=50, blank=True, default='')


def get_events(schedule):
    """
    Get the events from an ical.
    :param schedule: The oncall schedule we want events for
    :return: A list of dicts of event data
    """
    events = []
    for component in schedule.get_calendar_data().walk():
        if component.name == 'VEVENT':
            events.append({
                'start': component.decoded('dtstart'),
                'end': component.decoded('dtend'),
                'summary': component.decoded('summary'),
                'uid': component.decoded('uid'),
                'attendee': component.decoded('attendee'),
            })
    return events


class Shift(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()
    user = models.ForeignKey(User)
    uid = models.TextField()
    deleted = models.BooleanField(default=False)
    schedule = models.ForeignKey('Schedule', default=1)

    def __unicode__(self):
        deleted = ''
        if self.deleted:
            deleted = ' (deleted)'
        return "%s: %s to %s%s" % (self.user.username, self.start, self.end, deleted)


def get_duty_officers(schedule, at_time=None):
    """
    Return the users on duty for a given schedule and time
    :param schedule: The oncall schedule we're looking at
    :param at_time: The time we want to know about
    :return: List of users who are oncall
    """
    if not at_time:
        at_time = timezone.now()
    current_shifts = Shift.objects.filter(
        deleted=False,
        start__lt=at_time,
        end__gt=at_time,
        schedule=schedule,
    )
    if current_shifts:
        duty_officers = [shift.user for shift in current_shifts]
        return duty_officers
    else:
        if schedule.fallback_officer:
            return [schedule.fallback_officer]
        return []


def get_single_duty_officer(schedule, at_time=None):
    """
    Return one duty officer who is oncall
    :param schedule: The oncall schedule
    :param at_time: The time we want to know about
    :return: One oncall officer or nothing
    """
    officers = get_duty_officers(schedule, at_time)
    if len(officers) > 0:
        return officers[0]
    return ''


def get_all_duty_officers(at_time=None):
    """
    Find all oncall officers and the schedules they're oncall for
    :param at_time: The time we want to know about
    :return: dict of {oncall_officer: schedule}
    """
    out = defaultdict(list)

    for schedule in Schedule.objects.all():
        for user in get_duty_officers(schedule, at_time):
            out[user].append(schedule)

    return out


def get_all_fallback_officers():
    """
    Find all fallback officers and the schedules they're oncall for
    :param at_time:  The time we want to know about
    :return: dict of {fallback_officer: schedule}
    """
    out = defaultdict(list)

    for schedule in Schedule.objects.all():
        out[schedule.fallback_officer].append(schedule)

    return out


def get_fallback_officers(schedule):
    """
    Find the fallback officer
    :return: list of the fallback officer (for parity with get_duty_officers())
    """
    if schedule.fallback_officer:
        return [schedule.fallback_officer]
    return []


def update_shifts(schedule):
    """
    Update oncall Shifts for a given schedule
    :param schedule: The oncall schedule
    :return: none
    """
    events = get_events(schedule)
    users = User.objects.filter(is_active=True)
    user_lookup = {}
    for u in users:
        user_lookup[u.username.lower()] = u
    future_shifts = Shift.objects.filter(start__gt=timezone.now(),
                                         schedule=schedule)
    future_shifts.update(deleted=True)

    for event in events:
        summary = event['summary'].lower().strip()
        attendee = event['attendee'].lower().strip()

        if summary in user_lookup:
            e = summary
        elif attendee in user_lookup:
            e = attendee
        else:
            e = None

        if e is not None:
            user = user_lookup[e]
            try:
                s = Shift.objects.get(uid=event['uid'],
                                      schedule=schedule)
            except Shift.DoesNotExist:
                s = Shift(uid=event['uid'],
                          schedule=schedule)
            s.start = event['start']
            s.end = event['end']
            s.user = user
            s.deleted = False
            s.schedule = schedule
            s.save()


def delete_shifts(schedule):
    """
    Delete oncall Shifts for a given schedule
    :param schedule: the schedule
    :return none
    """
    shifts = Shift.objects.filter(schedule=schedule)
    for shift in shifts:
        shift.deleted = True
        shift.save()
