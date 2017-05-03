from django.db import models
from cabot.cabotapp.models import CHECK_TYPES, Service, StatusCheck
from cabot.metricsapp.api import run_metrics_check


class MetricsSourceBase(models.Model):
    class Meta:
        app_label = 'metricsapp'

    name = models.CharField(
        unique=True,
        max_length=30,
        help_text='Unique name for the data source',
    )

    def __unicode__(self):
        return self.name


class MetricsStatusCheckBase(StatusCheck):
    class Meta:
        app_label = 'metricsapp'

    IMPORTANCES = (
        (Service.ERROR_STATUS, 'Error'),
        (Service.CRITICAL_STATUS, 'Critical'),
    )

    source = models.ForeignKey(MetricsSourceBase)
    check_type = models.CharField(
        choices=CHECK_TYPES,
        max_length=30
    )
    warning_value = models.FloatField(
        null=True,
        blank=True,
        help_text='If this expression evaluates to False, the check will fail with a warning.'
    )
    high_alert_importance = models.CharField(
        max_length=30,
        choices=IMPORTANCES,
        default=Service.ERROR_STATUS,
        help_text='Severity level for a high alert failure. Critical alerts are for things you want to wake you '
                  'up, and errors are for things you can fix the next morning.'
    )
    high_alert_value = models.FloatField(
        null=True,
        blank=True,
        help_text='If this expression evaluates to False, the check will fail with an error or critical level alert.'
    )
    time_range = models.IntegerField(
        default=30,
        help_text='Time range in minutes the check gathers data for.',
    )

    def _run(self):
        """Run a status check"""
        return run_metrics_check(self)

    def get_series(self):
        """
        Implemented by subclasses.
        Parse raw data from a data source into the format
        status:
        error_message:
        error_code:
        raw:
        # Parsed data
        data:
          - series: a.b.c.d
            datapoints:
              - [timestamp, value]
              - [timestamp, value]
          - series: a.b.c.p.q
            datapoints:
              - [timestamp, value]
        :param check: the status check
        :return the parsed data
        """
        raise NotImplementedError('MetricsStatusCheckBase has no data source.')
