from django.core.exceptions import ValidationError
from django.forms import ModelForm
from elasticsearch.client import ClusterClient
from elasticsearch.exceptions import ConnectionError
from cabot.metricsapp.api.elastic import create_es_client
from cabot.metricsapp.models import ElasticsearchSource


class ElasticsearchSourceForm(ModelForm):
    class Meta:
        model = ElasticsearchSource

    def clean_urls(self):
        """Make sure the input urls are valid Elasticsearch hosts."""
        input_urls = self.cleaned_data['urls']

        # Create an Elasticsearch test client and see if a health check for the instance succeeds
        try:
            client = create_es_client(input_urls)
            ClusterClient(client).health()
            return input_urls
        except ConnectionError:
            raise ValidationError('Invalid Elasticsearch host url(s).')
