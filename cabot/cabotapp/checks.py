from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from polymorphic import PolymorphicModel
from django.db.models import F
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from cabot.cabotapp.models import (Service, StatusCheckResult, calculate_debounced_passing,
    serialize_recent_results,)
from celery.utils.log import get_task_logger
import urllib

CHECK_TYPES = (
    ('>', 'Greater than'),
    ('>=', 'Greater than or equal'),
    ('<', 'Less than'),
    ('<=', 'Less than or equal'),
    ('==', 'Equal to'),
)

logger = get_task_logger(__name__)

class CheckPlugin(PolymorphicModel):
    """
    Base class for polymorphic models. We're going to use
    proxy models for inheriting because it makes life much simpler,
    but this allows us to stick different methods etc on subclasses.

    You can work out what (sub)class a model is an instance of by accessing `instance.polymorphic_ctype.model`

    We are using django-polymorphic for polymorphism
    """

    plugin_title  = "Plugin Title"
    plugin_author = "Plugin Author"

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

    class Meta(PolymorphicModel.Meta):
        ordering = ['name']

    def __unicode__(self):
        return self.check_category + ' - ' + self.name

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
        self.check_category

    # def save(self, *args, **kwargs):
    #     if self.last_run:
    #         recent_results = list(self.recent_results())
    #         if calculate_debounced_passing(recent_results, self.debounce):
    #             self.calculated_status = Service.CALCULATED_PASSING_STATUS
    #         else:
    #             self.calculated_status = Service.CALCULATED_FAILING_STATUS
    #         self.cached_health = serialize_recent_results(recent_results)
    #         try:
    #             updated = CheckPlugin.objects.get(pk=self.pk)
    #         except CheckPlugin.DoesNotExist as e:
    #             logger.error('Cannot find myself (check %s) in the database, presumably have been deleted' % self.pk)
    #             return
    #     else:
    #         self.cached_health = ''
    #         self.calculated_status = Service.CALCULATED_PASSING_STATUS
    #     ret = super(CheckPlugin, self).save(*args, **kwargs)
    #     self.update_related_services()
    #     self.update_related_instances()
    #     return ret

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

    plugin_name = "Default"

    @property
    def get_create_url(self):
        quoted_url = urllib.quote_plus(self.plugin_name, safe='')
        return reverse('create-check', args=[quoted_url])

class CheckManager(models.Manager):
        def __init__(self):
            for check_plugin in CheckPlugin.__subclasses__():
                check_plugin.objects.get_or_create()
            return super(BaseManager, self).__init__()
