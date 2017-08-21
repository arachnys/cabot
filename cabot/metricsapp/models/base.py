from django.conf import settings
from django.db import models
from cabot.cabotapp.models import Service, StatusCheck
from cabot.metricsapp.api import run_metrics_check
from cabot.cabotapp.defs import CHECK_TYPES
from cabot.metricsapp.defs import METRIC_STATUS_TIME_RANGE_DEFAULT


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

    @property
    def update_url(self):
        if self.grafana_panel is not None:
            return 'grafana-edit'
        # Panels not from Grafana can only be edited by admins
        return 'check'

    IMPORTANCES = (
        (Service.ERROR_STATUS, 'Error'),
        (Service.CRITICAL_STATUS, 'Critical'),
    )

    source = models.ForeignKey('MetricsSourceBase')
    check_type = models.CharField(
        choices=CHECK_TYPES,
        max_length=30
    )
    warning_value = models.FloatField(
        null=True,
        blank=True,
        help_text='If this expression evaluates to False, the check will fail with a warning. Checks may have '
                  'both warning and high alert values, or only one.'
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
        default=METRIC_STATUS_TIME_RANGE_DEFAULT,
        help_text='Time range in minutes the check gathers data for.',
    )
    grafana_panel = models.ForeignKey(
        'GrafanaPanel',
        null=True
    )
    auto_sync = models.NullBooleanField(
        default=True,
        null=True,
        help_text='For Grafana status checks--should Cabot poll Grafana for dashboard updates and automatically '
                  'update the check?'
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

    def get_url_for_check(self):
        """Get the url for viewing this check"""
        return '{}://{}/check/{}/'.format(settings.WWW_SCHEME, settings.WWW_HTTP_HOST, self.id)

    def set_fields_from_grafana(self, fields):
        self.name = fields['name']
        self.source = fields['source']

        time_range = fields.get('time_range')
        if time_range is not None:
            self.time_range = time_range

        check_type = fields.get('check_type')
        if check_type is not None:
            self.check_type = check_type

        warning_value = fields.get('warning_value')
        if warning_value is not None:
            self.warning_value = warning_value

        high_alert_value = fields.get('high_alert_value')
        if high_alert_value is not None:
            self.high_alert_value = high_alert_value

        self.save()

    def get_status_image(self):
        """Return a Grafana png image for the check if it exists"""
        if self.grafana_panel is not None:
            return self.grafana_panel.get_rendered_image()
        return None

    def get_status_link(self):
        """Return a link from Grafana with more information about the check."""
        if self.grafana_panel is not None:
            return self.grafana_panel.modifiable_url
        return None
