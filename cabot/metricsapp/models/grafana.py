import logging
import requests
import urlparse
from django.core.exceptions import ValidationError
from django.db import models
from cabot.metricsapp import defs


logger = logging.getLogger(__name__)


class GrafanaInstance(models.Model):
    class Meta:
        app_label = 'metricsapp'

    name = models.CharField(
        unique=True,
        max_length=30,
        help_text='Unique name for Grafana site.'
    )
    url = models.CharField(
        max_length=100,
        help_text='Url of Grafana site.'
    )
    api_key = models.CharField(
        max_length=100,
        help_text='Grafana API token for authentication (http://docs.grafana.org/http_api/auth/).'
    )
    sources = models.ManyToManyField(
        'MetricsSourceBase',
        through='GrafanaDataSource',
        help_text='Metrics sources used by this Grafana site.'
    )

    _sessions = dict()

    def __unicode__(self):
        return self.name

    def clean(self, *args, **kwargs):
        """Make sure the input url/api key work"""
        response = self.get_request('api/search')

        try:
            response.raise_for_status()
        except requests.exception.HTTPError:
            raise ValidationError('Request to Grafana API failed.')

    @property
    def session(self):
        """A requests.session object with the correct authorization headers"""
        session = self._sessions.get(self.api_key)

        if session is None:
            session = requests.Session()
            session.headers.update({'Authorization': 'Bearer {}'.format(self.api_key)})
            self._sessions[self.api_key] = session

        return session

    def get_request(self, uri=''):
        """Make a request to the Grafana instance"""
        return self.session.get(urlparse.urljoin(self.url, uri))


class GrafanaDataSource(models.Model):
    """
    Intermediate model to match the name of a data source in a Grafana instance
    with the corresponding MetricsDataSource
    """
    class Meta:
        app_label = 'metricsapp'

    grafana_source_name = models.CharField(
        max_length=30,
        help_text='The name for a data source in grafana (e.g. metrics-stage")'
    )
    grafana_instance = models.ForeignKey('GrafanaInstance')
    metrics_source_base = models.ForeignKey('MetricsSourceBase')

    def __unicode__(self):
        return '{} ({}, {})'.format(self.grafana_source_name, self.metrics_source_base.name,
                                    self.grafana_instance.name)


class GrafanaPanel(models.Model):
    """
    Data about a Grafana panel.
    """
    class Meta:
        app_label = 'metricsapp'

    @property
    def modifiable_url(self):
        """Url with modifiable time range, dashboard link, etc"""
        if self.panel_url:
            return '{}&fullscreen'.format(self.panel_url.replace('dashboard-solo', 'dashboard'))
        return None

    def get_rendered_image(self):
        """Get a .png image of this panel"""
        # GrafanaInstance.get_request only takes the path
        panel_url = self.panel_url.replace(urlparse.urljoin(self.grafana_instance.url, '/'), '')
        rendered_image_url = urlparse.urljoin('render/', panel_url)
        rendered_image_url = '{}&width={}&height={}'.format(rendered_image_url,
                                                            defs.GRAFANA_RENDERED_IMAGE_WIDTH,
                                                            defs.GRAFANA_RENDERED_IMAGE_HEIGHT)

        # Unfortunately "$__all" works for the normal image but not render
        rendered_image_url = rendered_image_url.replace('$__all', 'All')

        try:
            image_request = self.grafana_instance.get_request(rendered_image_url)
            image_request.raise_for_status()
            return image_request.content

        except requests.exceptions.RequestException:
            logger.error('Failed to get Grafana panel image')
            return None

    grafana_instance = models.ForeignKey('GrafanaInstance')
    dashboard_uri = models.CharField(max_length=40)
    panel_id = models.IntegerField()
    series_ids = models.CharField(max_length=50)
    selected_series = models.CharField(max_length=50)
    panel_url = models.CharField(max_length=1024, null=True)
