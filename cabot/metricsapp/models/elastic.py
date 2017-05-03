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

    _clients = {}

    @property
    def client(self):
        """
        Return a global elasticsearch-py client for this ESSource (recommended practice
        for elasticsearch-py).
        """
        client_key = '{}_{}'.format(self.urls, self.timeout)
        client = self._clients.get(client_key)

        if not client:
            client = create_es_client(self.urls, self.timeout)
            self._clients[client_key] = client

        return client
