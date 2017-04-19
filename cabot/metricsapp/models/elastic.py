from django.db import models
from cabot.metricsapp.api import create_es_client
from .base import MetricsSourceBase


class ElasticsearchSource(MetricsSourceBase):
    class Meta:
        app_label = 'metricsapp'

    def __str__(self):
        return self.name

    urls = models.TextField(
        max_length=250,
        null=False,
        help_text='Comma-separated list of Elasticsearch hosts. '
                  'Format: "localhost" or "https://user:secret@localhost:443."'
    )
    index = models.TextField(
        max_length=50,
        default='*',
        help_text='Elasticsearch index name. Can include wildcards (*)',
    )
    timeout = models.IntegerField(
        default=60,
        help_text='Timeout for queries to this index.'
    )

    _client = None

    @property
    def client(self):
        """
        Return a global elasticsearch-py client for this ESSource (recommended practice
        for elasticsearch-py).
        """
        if self._client:
            return self._client
        return create_es_client(self.urls, self.timeout)
