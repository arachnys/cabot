from django.core.exceptions import ValidationError
from django.forms import ModelForm
from elasticsearch.client import ClusterClient
from elasticsearch.exceptions import ConnectionError
from cabot.metricsapp.api import create_es_client
from cabot.metricsapp.models import ElasticsearchSource, ElasticsearchStatusCheck
from cabot.cabotapp.views import StatusCheckForm


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


class ElasticsearchStatusCheckForm(StatusCheckForm):
    class Meta:
        model = ElasticsearchStatusCheck
        fields = (
            'name',
            'source',
            'queries',
            'check_type',
            'warning_value',
            'high_alert_importance',
            'high_alert_value',
            'consecutive_failures',
            'time_range',
            'frequency',
            'active',
            'retries',
            'ignore_final_data_point',
            'use_activity_counter',
            'runbook',
        )

    def __init__(self, *args, **kwargs):
        ret = super(ElasticsearchStatusCheckForm, self).__init__(*args, **kwargs)
        self.fields['source'].queryset = ElasticsearchSource.objects.all()
        return ret
