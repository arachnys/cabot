from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from polymorphic import PolymorphicModel
from django.db.models import F
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from celery.exceptions import SoftTimeLimitExceeded

from .jenkins import get_job_status
from .alert import (
    send_alert,
    send_alert_update,
    AlertPlugin,
    AlertPluginUserData,
    update_alert_plugins
)
from .calendar import get_events
from .graphite import parse_metric
from .graphite import get_data
from .tasks import update_service, update_instance
from datetime import datetime, timedelta
from django.utils import timezone

import json
import re
import time
import os
import subprocess
import itertools

import requests
from celery.utils.log import get_task_logger

RAW_DATA_LIMIT = 5000

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


def calculate_debounced_passing(recent_results, debounce=0):
    """
    `debounce` is the number of previous failures we need (not including this)
    to mark a search as passing or failing
    Returns:
      True if passing given debounce factor
      False if failing
    """
    if not recent_results:
        return True
    debounce_window = recent_results[:debounce + 1]
    for r in debounce_window:
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
        help_text='Gist, Hackpad or Refheap js embed with recovery instructions e.g. https://you.hackpad.com/some_document.js'
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
            # Don't alert every time
            if self.overall_status == self.WARNING_STATUS:
                if self.last_alert_sent and (timezone.now() - timedelta(minutes=settings.NOTIFICATION_INTERVAL)) < self.last_alert_sent:
                    return
            elif self.overall_status in (self.CRITICAL_STATUS, self.ERROR_STATUS):
                if self.last_alert_sent and (timezone.now() - timedelta(minutes=settings.ALERT_INTERVAL)) < self.last_alert_sent:
                    return
            self.last_alert_sent = timezone.now()
        else:
            # We don't count "back to normal" as an alert
            self.last_alert_sent = None
        self.save()
        if self.unexpired_acknowledgement():
            send_alert_update(self, duty_officers=get_duty_officers())
        else:
            self.snapshot.did_send_alert = True
            self.snapshot.save()
            send_alert(self, duty_officers=get_duty_officers())

    def unexpired_acknowledgements(self):
        acknowledgements = self.alertacknowledgement_set.all().filter(
            time__gte=timezone.now()-timedelta(minutes=settings.ACKNOWLEDGEMENT_EXPIRY),
            cancelled_time__isnull=True,
        ).order_by('-time')
        return acknowledgements

    def acknowledge_alert(self, user):
        if self.unexpired_acknowledgements(): # Don't allow users to jump on each other
            return None
        acknowledgement = AlertAcknowledgement.objects.create(
            user=user,
            time=timezone.now(),
            service=self,
        )

    def remove_acknowledgement(self, user):
        self.unexpired_acknowledgements().update(
            cancelled_time=timezone.now(),
            cancelled_user=user,
        )

    def unexpired_acknowledgement(self):
        try:
            return self.unexpired_acknowledgements()[0]
        except:
            return None

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
        help_text='Severity level of a failure. Critical alerts are for failures you want to wake you up at 2am, Errors are things you can sleep through but need to fix in the morning, and warnings for less important things.'
    )
    frequency = models.IntegerField(
        default=5,
        help_text='Minutes between each check.',
    )
    debounce = models.IntegerField(
        default=0,
        null=True,
        help_text='Number of successive failures permitted before check will be marked as failed. Default is 0, i.e. fail on first failure.'
    )
    created_by = models.ForeignKey(User, null=True)
    calculated_status = models.CharField(
        max_length=50, choices=Service.STATUSES, default=Service.CALCULATED_PASSING_STATUS, blank=True)
    last_run = models.DateTimeField(null=True)
    cached_health = models.TextField(editable=False, null=True)

    # Graphite checks
    metric = models.TextField(
        null=True,
        help_text='fully.qualified.name of the Graphite metric you want to watch. This can be any valid Graphite expression, including wildcards, multiple hosts, etc.',
    )
    check_type = models.CharField(
        choices=CHECK_TYPES,
        max_length=100,
        null=True,
    )
    value = models.TextField(
        null=True,
        help_text='If this expression evaluates to true, the check will fail (possibly triggering an alert).',
    )
    expected_num_hosts = models.IntegerField(
        default=0,
        null=True,
        help_text='The minimum number of data series (hosts) you expect to see.',
    )
    allowed_num_failures = models.IntegerField(
        default=0,
        null=True,
        help_text='The maximum number of data series (metrics) you expect to fail. For example, you might be OK with 2 out of 3 webservers having OK load (1 failing), but not 1 out of 3 (2 failing).',
    )

    # HTTP checks
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
    text_match = models.TextField(
        blank=True,
        null=True,
        help_text='Regex to match against source of page.',
    )
    status_code = models.TextField(
        default=200,
        null=True,
        help_text='Status code expected from endpoint.'
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

    # Jenkins checks
    max_queued_build_time = models.IntegerField(
        null=True,
        blank=True,
        help_text='Alert if build queued for more than this many minutes.',
    )

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
            logger.error(u"Error performing check: %s" % (e.message,))
            result.error = u'Error in performing check: %s' % (e.message,)
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
            if calculate_debounced_passing(recent_results, self.debounce):
                self.calculated_status = Service.CALCULATED_PASSING_STATUS
            else:
                self.calculated_status = Service.CALCULATED_FAILING_STATUS
            self.cached_health = serialize_recent_results(recent_results)
            try:
                updated = StatusCheck.objects.get(pk=self.pk)
            except StatusCheck.DoesNotExist as e:
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
        new_check.last_run = None
        new_check.save()
        for linked in list(inst_set) + list(serv_set):
            linked.status_checks.add(new_check)
        return new_check.pk

    def update_related_services(self):
        services = self.service_set.all()
        for service in services:
            update_service.delay(service.id)

    def update_related_instances(self):
        instances = self.instance_set.all()
        for instance in instances:
            update_instance.delay(instance.id)


class ICMPStatusCheck(StatusCheck):

    class Meta(StatusCheck.Meta):
        proxy = True

    @property
    def check_category(self):
        return "ICMP/Ping Check"

    def _run(self):
        result = StatusCheckResult(check=self)
        instances = self.instance_set.all()
        target = self.instance_set.get().address

        # We need to read both STDOUT and STDERR because ping can write to both, depending on the kind of error. Thanks a lot, ping.
        ping_process = subprocess.Popen("ping -c 1 " + target, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        response = ping_process.wait()

        if response == 0:
            result.succeeded = True
        else:
            output = ping_process.stdout.read()
            result.succeeded = False
            result.error = output

        return result


def minimize_targets(targets):
    split = [target.split(".") for target in targets]

    prefix_nodes_in_common = 0
    for i, nodes in enumerate(itertools.izip(*split)):
        if any(node != nodes[0] for node in nodes):
            prefix_nodes_in_common = i
            break
    split = [nodes[prefix_nodes_in_common:] for nodes in split]

    suffix_nodes_in_common = 0
    for i, nodes in enumerate(reversed(zip(*split))):
        if any(node != nodes[0] for node in nodes):
            suffix_nodes_in_common = i
            break
    if suffix_nodes_in_common:
        split = [nodes[:-suffix_nodes_in_common] for nodes in split]

    return [".".join(nodes) for nodes in split]


class GraphiteStatusCheck(StatusCheck):

    class Meta(StatusCheck.Meta):
        proxy = True

    @property
    def check_category(self):
        return "Metric check"

    def format_error_message(self, failures, actual_hosts, hosts_by_target):
        if actual_hosts < self.expected_num_hosts:
            return "Hosts missing | %d/%d hosts" % (
                actual_hosts, self.expected_num_hosts)
        elif actual_hosts > 1:
            threshold = float(self.value)
            failures_by_host = ["%s: %s %s %0.1f" % (
                hosts_by_target[target], value, self.check_type, threshold)
                for target, value in failures]
            return ", ".join(failures_by_host)
        else:
            target, value = failures[0]
            return "%s %s %0.1f" % (value, self.check_type, float(self.value))

    def _run(self):
        result = StatusCheckResult(check=self)

        failures = []
        graphite_output = parse_metric(self.metric, mins_to_check=self.frequency)

        try:
            result.raw_data = json.dumps(graphite_output['raw'])
        except:
            result.raw_data = graphite_output['raw']

        if graphite_output["error"]:
            result.succeeded = False
            result.error = graphite_output["error"]
            return result

        if graphite_output['num_series_with_data'] > 0:
            result.average_value = graphite_output['average_value']
            for s in graphite_output['series']:
                if not s["values"]:
                    continue
                failure_value = None
                if self.check_type == '<':
                    if float(s['min']) < float(self.value):
                        failure_value = s['min']
                elif self.check_type == '<=':
                    if float(s['min']) <= float(self.value):
                        failure_value = s['min']
                elif self.check_type == '>':
                    if float(s['max']) > float(self.value):
                        failure_value = s['max']
                elif self.check_type == '>=':
                    if float(s['max']) >= float(self.value):
                        failure_value = s['max']
                elif self.check_type == '==':
                    if float(self.value) in s['values']:
                        failure_value = float(self.value)
                else:
                    raise Exception(u'Check type %s not supported' %
                                    self.check_type)

                if not failure_value is None:
                    failures.append((s["target"], failure_value))

        if len(failures) > self.allowed_num_failures:
            result.succeeded = False
        elif graphite_output['num_series_with_data'] < self.expected_num_hosts:
            result.succeeded = False
        else:
            result.succeeded = True

        if not result.succeeded:
            targets = [s["target"] for s in graphite_output["series"]]
            hosts = minimize_targets(targets)
            hosts_by_target = dict(zip(targets, hosts))

            result.error = self.format_error_message(
                failures,
                graphite_output['num_series_with_data'],
                hosts_by_target,
            )

        return result


class HttpStatusCheck(StatusCheck):

    class Meta(StatusCheck.Meta):
        proxy = True

    @property
    def check_category(self):
        return "HTTP check"

    def _run(self):
        result = StatusCheckResult(check=self)

        auth = None
        if self.username or self.password:
            auth = (self.username, self.password)

        try:
            resp = requests.get(
                self.endpoint,
                timeout=self.timeout,
                verify=self.verify_ssl_certificate,
                auth=auth,
                headers={
                    "User-Agent": settings.HTTP_USER_AGENT,
                },
            )
        except requests.RequestException as e:
            result.error = u'Request error occurred: %s' % (e.message,)
            result.succeeded = False
        else:
            if self.status_code and resp.status_code != int(self.status_code):
                result.error = u'Wrong code: got %s (expected %s)' % (
                    resp.status_code, int(self.status_code))
                result.succeeded = False
                result.raw_data = resp.content
            elif self.text_match:
                if not re.search(self.text_match, resp.content):
                    result.error = u'Failed to find match regex /%s/ in response body' % self.text_match
                    result.raw_data = resp.content
                    result.succeeded = False
                else:
                    result.succeeded = True
            else:
                result.succeeded = True
        return result


class JenkinsStatusCheck(StatusCheck):

    class Meta(StatusCheck.Meta):
        proxy = True

    @property
    def check_category(self):
        return "Jenkins check"

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
            result.succeeded = True
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

    class Meta:
        ordering = ['-time_complete']
        index_together = (('check', 'time_complete'),)

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
        """
        Time taken by check in ms
        """
        try:
            diff = self.time_complete - self.time
            return (diff.microseconds + (diff.seconds + diff.days * 24 * 3600) * 10**6) / 1000
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


class AlertAcknowledgement(models.Model):

    time = models.DateTimeField()
    user = models.ForeignKey(User)
    service = models.ForeignKey(Service)
    cancelled_time = models.DateTimeField(null=True, blank=True)
    cancelled_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='cancelleduser_set'
    )

    def unexpired(self):
        return self.expires() > timezone.now()

    def expires(self):
        return self.time + timedelta(minutes=settings.ACKNOWLEDGEMENT_EXPIRY)

class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')

    def user_data(self):
        for user_data_subclass in AlertPluginUserData.__subclasses__():
            user_data = user_data_subclass.objects.get_or_create(user=self, title=user_data_subclass.name)
        return AlertPluginUserData.objects.filter(user=self)

    def __unicode__(self):
        return 'User profile: %s' % self.user.username

    def save(self, *args, **kwargs):
        # Enforce uniqueness
        if self.fallback_alert_user:
            profiles = UserProfile.objects.exclude(id=self.id)
            profiles.update(fallback_alert_user=False)
        return super(UserProfile, self).save(*args, **kwargs)

    @property
    def prefixed_mobile_number(self):
        return '+%s' % self.mobile_number

    mobile_number = models.CharField(max_length=20, blank=True, default='')
    hipchat_alias = models.CharField(max_length=50, blank=True, default='')
    fallback_alert_user = models.BooleanField(default=False)


class Shift(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()
    user = models.ForeignKey(User)
    uid = models.TextField()
    deleted = models.BooleanField(default=False)

    def __unicode__(self):
        deleted = ''
        if self.deleted:
            deleted = ' (deleted)'
        return "%s: %s to %s%s" % (self.user.username, self.start, self.end, deleted)


def get_duty_officers(at_time=None):
    """Returns a list of duty officers for a given time or now if none given"""
    duty_officers = []
    if not at_time:
        at_time = timezone.now()
    current_shifts = Shift.objects.filter(
        deleted=False,
        start__lt=at_time,
        end__gt=at_time,
    )
    if current_shifts:
        duty_officers = [shift.user for shift in current_shifts]
        return duty_officers
    else:
        try:
            u = UserProfile.objects.get(fallback_alert_user=True)
            return [u.user]
        except UserProfile.DoesNotExist:
            return []


def update_shifts():
    events = get_events()
    users = User.objects.filter(is_active=True)
    user_lookup = {}
    for u in users:
        user_lookup[u.username.lower()] = u
    future_shifts = Shift.objects.filter(start__gt=timezone.now())
    future_shifts.update(deleted=True)

    for event in events:
        e = event['summary'].lower().strip()
        if e in user_lookup:
            user = user_lookup[e]
            try:
                s = Shift.objects.get(uid=event['uid'])
            except Shift.DoesNotExist:
                s = Shift(uid=event['uid'])
            s.start = event['start']
            s.end = event['end']
            s.user = user
            s.deleted = False
            s.save()
