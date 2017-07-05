import json
import logging
import time
from collections import defaultdict
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import escape
from elasticsearch_dsl import MultiSearch, Search
from cabot.metricsapp.api import create_es_client, validate_query
from cabot.metricsapp.defs import HIDDEN_METRIC_SUFFIX
from .base import MetricsSourceBase, MetricsStatusCheckBase


logger = logging.getLogger(__name__)


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
        help_text=escape('Elasticsearch index name. Can include wildcards ("*") or date math expressions '
                         '("<static_name{date_math_expr{date_format|time_zone}}\>"). For example, an index could be '
                         '"<metrics-{now/d}>,<metrics-{now/d-1d}>", resolving to "metrics-yyyy-mm-dd,'
                         'metrics-yyyy-mm-dd", for the past 2 days of metrics.'),
    )
    timeout = models.IntegerField(
        default=settings.ELASTICSEARCH_TIMEOUT,
        help_text='Timeout for queries to this index.'
    )
    max_concurrent_searches = models.IntegerField(
        default=settings.ELASTICSEARCH_MAX_CONCURRENT_SEARCHES,
        null=True,
        blank=True,
        help_text='Maximum concurrent searches the multi search api can run.'
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


class ElasticsearchStatusCheck(MetricsStatusCheckBase):
    class Meta:
        app_label = 'metricsapp'

    @property
    def description(self):
        desc = []
        if self.warning_value is not None:
            desc.append('Warning: {} {}'.format(self.check_type, self.warning_value))
        if self.high_alert_value is not None:
            desc.append('{}: {} {}'.format(self.high_alert_importance.title(), self.check_type, self.high_alert_value))
        return '; '.join(desc)

    metrics_update_url = 'grafana-es-update'
    refresh_url = 'grafana-es-refresh'

    icon = 'glyphicon glyphicon-stats'

    queries = models.TextField(
        max_length=10000,
        help_text='List of raw json Elasticsearch queries. Format: [q] or [q1, q2, ...]. '
                  'Query guidelines: all aggregations should be named "agg." The most '
                  'internal aggregation must be a date_histogram. Metrics names should be '
                  'the same as the metric types (e.g., "max", "min", "avg").'
    )

    def clean(self, *args, **kwargs):
        """Validate the query"""
        try:
            queries = json.loads(self.queries)
        except ValueError:
            raise ValidationError('Queries are not json-parsable')

        for query in queries:
            validate_query(query)

    def get_series(self):
        """
        Get the relevant data for a check from Elasticsearch and parse it
        into a generic format.
        :param check: the ElasticsearchStatusCheck
        :return data in the format
            status:
            error_message:
            error_code:
            raw:
            data:
              - series: a.b.c.d
                datapoints:
                  - [timestamp, value]
                  - [timestamp, value]
              - series: a.b.c.p.q
                datapoints:
                  - [timestamp, value]
                check:
        """
        # Error will be set to true if we encounter an error
        parsed_data = dict(raw=[], error=False, data=[])
        source = ElasticsearchSource.objects.get(name=self.source.name)
        multisearch = MultiSearch()

        if source.max_concurrent_searches is not None:
            multisearch.params(max_concurrent_searches=source.max_concurrent_searches)

        for query in json.loads(self.queries):
            multisearch = multisearch.add(Search.from_dict(query))

        try:
            responses = multisearch.using(source.client).index(source.index).execute()

            for response in responses:
                raw_data = response.to_dict()
                parsed_data['raw'].append(raw_data)

                if raw_data['hits']['hits'] == []:
                    continue

                data = self._parse_es_response([raw_data['aggregations']])
                if data == []:
                    continue

                parsed_data['data'].extend(data)

        except Exception as e:
            logger.exception('Error executing Elasticsearch query: {}'.format(query))
            parsed_data['error_code'] = type(e).__name__
            parsed_data['error_message'] = str(e)
            parsed_data['error'] = True

        # If there's no data, fill in a 0 so the check doesn't fail.
        # TODO: fill value could be set based on "Stacking & Null value" in Grafana
        if parsed_data['data'] == []:
            parsed_data['data'].append(dict(series='no_data_fill_0', datapoints=[[int(time.time()), 0]]))

        return parsed_data

    def _parse_es_response(self, series):
        """
        Parse the Elasticsearch json response and create an output list containing only
        points within the time range for this check.
        :param series: 'aggregations' part of the response from Elasticsearch
        :return: list in the format [{series: [timestamp, value]}]
        """
        earliest_point = time.time() - self.time_range * 60
        output = []
        data = defaultdict(list)
        for metric, (timestamp, value) in self._parse_series(series):
            if timestamp > earliest_point:
                data[metric].append([timestamp, value])

        for series, datapoints in data.iteritems():
            # The last bucket may not have complete data, so we'll ignore it
            datapoints = sorted(datapoints, key=lambda x: x[0])
            output.append(dict(series=series, datapoints=datapoints[:-1]))

        return output

    def _parse_series(self, series, series_name=None):
        """
        Parse the Elasticsearch json response and generate data for each datapoint
        :param series: the 'aggregations' part of the response from Elasticsearch
        :param series_name: the name for the series ('key1.key2. ... .metric')
        :return: (series, (timestamp, datapoint)) pairs
        """
        for subseries in series:
            # If there are no more aggregations, we've reached the metric
            if subseries.get('agg') is None:
                results = self._get_metric_data(subseries, series_name)

            else:
                # New name is "series_name.subseries_name" (if they exist)
                key = subseries.get('key')
                subseries_name = '.'.join(filter(None, [series_name, key]))
                results = self._parse_series(subseries['agg']['buckets'], series_name=subseries_name)

            for result in results:
                yield result

    def _valid_point(self, point):
        return point not in ['None', 'NaN', None]

    def _get_metric_data(self, subseries, series_name):
        """
        Given the part of the ES response grouped by timestamp, generate
        (series, (timestamp, value)) pairs for each metric
        :param subseries: subset of the Elasticsearch response dealing with metric info
        :param series_name: "agg1.agg2..."
        :return: (series, (timestamp, value)) pairs for each metric in the response
        """
        timestamp = subseries['key'] / 1000

        for metric, value_dict in subseries.iteritems():
            # Ignore hidden metrics and things that are not actually the metric field--timestamp, doc_count, etc.
            if type(value_dict) != dict or HIDDEN_METRIC_SUFFIX in metric:
                continue

            if 'value' in value_dict:
                value = value_dict['value']
                if self._valid_point(value):
                    # Series_name might be none if there are no aggs
                    metric_name = '.'.join(filter(None, [series_name, metric]))
                    yield (metric_name, (timestamp, value_dict['value']))

            elif 'values' in value_dict:
                for submetric_name, value in value_dict['values'].iteritems():
                    if self._valid_point(value):
                        metric_name = '.'.join(filter(None, [series_name, submetric_name]))
                        yield (metric_name, (timestamp, value))

            else:
                raise NotImplementedError('Unsupported metric: {}.'.format(metric))

    def set_fields_from_grafana(self, fields):
        self.queries = json.dumps(fields['queries'])
        super(ElasticsearchStatusCheck, self).set_fields_from_grafana(fields)
