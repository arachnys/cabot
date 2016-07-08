import itertools
import json
import re
import subprocess
import time
from datetime import timedelta

import requests
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from django.conf import settings
from polymorphic.models import PolymorphicModel
from django.db import models
from django.db.models import F
from django.db.models import signals
from django.dispatch import receiver
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from celery.exceptions import SoftTimeLimitExceeded

from .alert import (
    send_alert_update,
    )
from .calendar import get_events
from .tasks import update_service, update_instance
from datetime import datetime, timedelta
from django.utils import timezone
from picklefield.fields import PickledObjectField

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
    """
    Base model for Services and Instances. It handles the StatusChecks
    associated with them.
    """

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
        'plugins.AlertPluginModel',
        blank=True,
        help_text='Alerts channels through which you wish to be notified'
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
                if self.last_alert_sent and (
                    timezone.now() - timedelta(minutes=settings.NOTIFICATION_INTERVAL)) < self.last_alert_sent:
                    return
            elif self.overall_status in (self.CRITICAL_STATUS, self.ERROR_STATUS):
                if self.last_alert_sent and (
                    timezone.now() - timedelta(minutes=settings.ALERT_INTERVAL)) < self.last_alert_sent:
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

	    users = self.users_to_notify.filter(is_active=True)
	    for alert in self.alerts.all():
		try:
		    alert.send_alert(self, users, get_duty_officers())
		except Exception as e:
		    logger.exception('Could not send %s alert: %s' % (alert.name, e))

    def unexpired_acknowledgements(self):
        acknowledgements = self.alertacknowledgement_set.all().filter(
            time__gte=timezone.now() - timedelta(minutes=settings.ACKNOWLEDGEMENT_EXPIRY),
            cancelled_time__isnull=True,
        ).order_by('-time')
        return acknowledgements

    def acknowledge_alert(self, user):
        if self.unexpired_acknowledgements():  # Don't allow users to jump on each other
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
    
    def get_status_message(self, include_checks_failing=True):
        template_name = 'cabotapp/service_status_message.html'
        message = render_to_string(template_name,
                {
                    'service': self,
                    'include_checks_failing': include_checks_failing,
                    'scheme': settings.WWW_SCHEME,
                    'host': settings.WWW_HTTP_HOST
                })
        return message.rstrip() # Return and remove trailing whitespace


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

    def delete(self, *args, **kwargs):
        return super(Instance, self).delete(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('instance', args=[self.pk])


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


class StatusCheckVariable(models.Model):
    status_check = models.ForeignKey('StatusCheck')
    key = models.CharField(max_length=128)
    value = PickledObjectField(null=True)

    def __unicode__(self):
        return '{}: {}'.format(self.key, self.value)

    class Meta:
        unique_together = ('status_check', 'key')


class StatusCheck(models.Model):

    # Each StatusCheck object must be attacked to plugin which is used to
    # run the check and to define the configuration form.
    check_plugin = models.ForeignKey(
        'plugins.StatusCheckPluginModel',
        related_name='status_check',
        editable=False
	)

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
                  'Errors are things you can sleep through but need to fix in the morning, and warnings for less '
                  'important things.'
    )
    frequency = models.IntegerField(
        default=5,
        help_text='Minutes between each check.',
    )
    debounce = models.IntegerField(
        default=0,
        null=True,
        help_text='Number of successive failures permitted before check will be marked as failed. Default is 0, '
                  'i.e. fail on first failure.'
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
        return StatusCheckResult.objects.filter(status_check=self).order_by('-id').defer('raw_data')[:10]

    def set_variable(self, key, value):
        variable, created = StatusCheckVariable.objects.get_or_create(status_check=self, key=key)
        variable.value = value
        variable.save()
        return variable.value

    def get_variable(self, key):
        # First try and get the value, then the default and finally None.
        try:
            return StatusCheckVariable.objects.get(status_check=self, key=key).value
        except:
            try:
                return self.check_plugin.plugin_class.config_form().fields[key].initial
            except:
                return None

    def get_absolute_url(self):
        return reverse('check', args=[self.pk])

    def get_absolute_update_url(self):
        return reverse('update-check', args=[self.pk])

    def get_absolute_duplicate_url(self):
        return reverse('duplicate-check', args=[self.pk])

    def get_absolute_run_url(self):
        return reverse('run-check', args=[self.pk])

    def last_result(self):
        try:
            return StatusCheckResult.objects.filter(
                    status_check=self).order_by('-id').defer('raw_data')[0]
        except:
            return None

    def run(self):
        start = timezone.now()
        result = StatusCheckResult(status_check=self)
        result = self.check_plugin.plugin_class.run(self, result)
        try:
            result = StatusCheckResult(status_check=self)
            result = self.check_plugin.plugin_class.run(self, result)
        except SoftTimeLimitExceeded as e:
            result = StatusCheckResult(status_check=self)
            result.error = u'Error in performing check: ' + \
                            'Celery soft time limit exceeded'
            result.succeeded = False
        except Exception as e:
            result = StatusCheckResult(status_check=self)
            logger.error(u"Error performing check: %s" % (e.message,))
            result.error = u'Error in performing check: %s' % (e.message,)
            result.succeeded = False
        finish = timezone.now()
        result.time = start
        result.time_complete = finish
        result.save()
        self.last_run = finish
        self.save()
        return result

    def get_distinct_field_names(self, check_plugin=None):
        if check_plugin is None:
            check_plugin = self.check_plugin
        return check_plugin.plugin_class.config_form().fields

    def __init__(self, *args, **kwargs):

        # Any custom config variables that are passed to __init__ are
        # added added as attributes to the status check. This will only
        # happen on StatusCheck creation.
        check_plugin = kwargs.get('check_plugin', None)
        if check_plugin:
            for field_name in self.get_distinct_field_names(check_plugin=check_plugin):
                field_val = kwargs.pop(field_name, None)
                if field_val:
                    # Set the variable if it passed
                    setattr(self, field_name, field_val)
                else:
                    # Otherwise get initial value
                    try:
                        initial_val = check_plugin.plugin_class.config_form().fields[field_name].initial
                        setattr(self, field_name, initial_val)
                    except:
                        setattr(self, field_name, None)

        ret = super(StatusCheck, self).__init__(*args, **kwargs)

        # Fetch 
        if self.pk and self.check_plugin:
            for field in self.get_distinct_field_names():
                setattr(self, field, self.get_variable(field))

        return ret

    def save(self, *args, **kwargs):

        # Update calculated status
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
        
        #
        # Save custom variables
        #
        field_names = self.get_distinct_field_names()
        field_dict = {}
        for field in self.get_distinct_field_names():
            field_dict[field] = getattr(self, field)
        # Field validation
        form = self.check_plugin.plugin_class.config_form(field_dict)
        if not form.is_valid():
            raise ValidationError('{} did not validate: {}'.format(self.name, form.errors))
        for key, value in form.cleaned_data.items():
            self.set_variable(key, value)

        return ret

    def duplicate(self, inst_set=(), serv_set=()):
        self_pk = self.pk

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

    def description(self):
        return self.check_plugin.plugin_class.description(self)


class StatusCheckResult(models.Model):
    """
    We use the same StatusCheckResult model for all check types,
    because really they are not so very different.

    Checks don't have to use all the fields, so most should be
    nullable
    """
    status_check = models.ForeignKey(StatusCheck)
    time = models.DateTimeField(null=False, db_index=True)
    time_complete = models.DateTimeField(null=True, db_index=True)
    raw_data = models.TextField(null=True)
    succeeded = models.BooleanField(default=False)
    error = models.TextField(null=True)

    # Jenkins specific
    job_number = models.PositiveIntegerField(null=True)

    class Meta:
        ordering = ['-time_complete']
        index_together = (('status_check', 'time_complete'),)

    def __unicode__(self):
        return '%s: %s @%s' % (self.status, self.status_check.name, self.time)

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
            return (diff.microseconds + (diff.seconds + diff.days * 24 * 3600) * 10 ** 6) / 1000
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


@receiver(signals.post_init, sender=User)
def patch_user(sender, instance, **kwargs):
    from cabot.plugins.models import AlertPluginModel, AlertPluginUserData
    plugins = [p for p in AlertPluginModel.objects.all() if p.plugin_class and p.plugin_class.user_config_form]

    for plugin in plugins:

        class UserSettingsObj(object):

            def __init__(cls, plugin=plugin, instance=instance):
                cls.plugin = plugin
                cls.instance = instance

            def __getattr__(cls, key):
                if not key in cls.plugin.plugin_class.user_config_form().fields:
                    raise AttributeError('{} has no user variable {}'.format(cls.plugin.full_name, key))
                try:
                    return AlertPluginUserData.objects.get(
                        plugin = cls.plugin,
                        user = cls.instance,
                        key = key
                        ).value
                except:
                    return ''

            def __setattr__(cls, key, item):
                if key in ['plugin', 'instance']:
                    return super(UserSettingsObj, cls).__setattr__(key, item)
                
                if not key in cls.plugin.plugin_class.user_config_form().fields:
                    raise AttributeError('{} has no user variable {}.'.format(cls.plugin.full_name, key))
                var, created = AlertPluginUserData.objects.get_or_create(
                        plugin = cls.plugin,
                        user = cls.instance,
                        key = key,
                    )
                var.value = item
                var.save()
                return var.value
        

        dict_name = '{}_settings'.format(plugin.slug)
        User.add_to_class(dict_name, UserSettingsObj())

#
# DEPRECATED
# Use StatusCheckUserData to store data
#
class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')

    def user_data(self):
        return {}

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
