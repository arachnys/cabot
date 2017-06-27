import json
import os
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from elasticsearch_dsl import Search
from elasticsearch_dsl.response import Response
from mock import patch
from cabot.cabotapp.models import Service
from cabot.metricsapp.api import validate_query
from cabot.metricsapp.defs import ES_VALIDATION_MSG_PREFIX
from cabot.metricsapp.models import ElasticsearchSource, ElasticsearchStatusCheck


class TestElasticsearchSource(TestCase):
    def setUp(self):
        self.es_source = ElasticsearchSource.objects.create(
            name='elastigirl',
            urls='localhost',
            index='i'
        )

    def test_client(self):
        client = self.es_source.client
        self.assertIn('localhost', repr(client))

    def test_multiple_clients(self):
        self.es_source.urls = 'localhost,127.0.0.1'
        self.es_source.save()
        client = self.es_source.client
        self.assertIn('localhost', repr(client))
        self.assertIn('127.0.0.1', repr(client))

    def test_client_whitespace(self):
        """Whitespace should be stripped from the urls"""
        self.es_source.urls = '\nlocalhost,       globalhost'
        self.es_source.save()
        client = self.es_source.client
        self.assertIn('localhost', repr(client))
        self.assertIn('globalhost', repr(client))
        self.assertNotIn('\nlocalhost', repr(client))
        self.assertNotIn(' globalhost', repr(client))


def get_content(filename):
    path = os.path.join(os.path.dirname(__file__), 'fixtures/elastic/{}'.format(filename))
    with open(path) as f:
        return f.read()


def empty_es_response(*args):
    return Response(Search(), [])


def get_json_file(file):
    path = os.path.join(os.path.dirname(__file__), 'fixtures/elastic/{}'.format(file))
    with open(path) as f:
        return json.loads(f.read())


def fake_es_response(*args):
    return [Response(Search(), response) for response in get_json_file('es_response.json')]


def fake_es_multiple_metrics_terms(*args):
    return [Response(Search(), response) for response in get_json_file('es_multiple_metrics_terms.json')]


def fake_es_percentile(*args):
    return [Response(Search(), response) for response in get_json_file('es_percentile.json')]


def fake_es_multiple_terms(*args):
    return [Response(Search(), response) for response in get_json_file('es_multiple_terms.json')]


def fake_es_multiple_queries(*args):
    return [Response(Search(), response) for response in get_json_file('es_response.json')] + \
           [Response(Search(), response) for response in get_json_file('es_percentile.json')]

def fake_es_none(*args):
    return [Response(Search(), response) for response in get_json_file('es_none_nan.json')]


def mock_time():
    return 1491577200.0


class TestElasticsearchStatusCheck(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('user')
        self.es_source = ElasticsearchSource.objects.create(
            name='es',
            urls='localhost',
            index='test-index-pls-ignore'
        )
        self.es_check = ElasticsearchStatusCheck.objects.create(
            name='checkycheck',
            created_by=self.user,
            source=self.es_source,
            check_type='>=',
            warning_value=3.5,
            high_alert_importance='CRITICAL',
            high_alert_value=3.0,
            queries='[{"aggs": {"agg": {"terms": {"field": "a1"},'
                    '"aggs": {"agg": {"terms": {"field": "b2"},'
                    '"aggs": {"agg": {"date_histogram": {"field": "@timestamp","interval": "hour"},'
                    '"aggs": {"max": {"max": {"field": "timing"}}}}}}}}}}]',
            time_range=10000
        )

    @patch('cabot.metricsapp.models.elastic.MultiSearch.execute', fake_es_response)
    @patch('time.time', mock_time)
    def test_query(self):
        # Test output series
        series = self.es_check.get_series()
        self.assertFalse(series['error'])
        self.assertEqual(series['raw'], get_json_file('es_response.json'))
        data = series['data']
        self.assertEqual(len(data), 1)

        data = data[0]
        self.assertEqual(str(data['series']), 'avg')
        self.assertEqual(data['datapoints'], [[1491552000, 4.9238095238095], [1491555600, 4.7958115183246],
                                              [1491559200, 3.53005464480873], [1491562800, 4.04651162790697],
                                              [1491566400, 4.8390501319261], [1491570000, 4.51913477537437],
                                              [1491573600, 4.4642857142857]])

        # Test check result
        result = self.es_check._run()
        self.assertTrue(result.succeeded)
        self.assertIsNone(result.error)

    def test_invalid_query(self):
        """Test that an invalid Elasticsearch query is caught in save()"""
        self.es_check.queries = 'definitely not elasticsearch at all'
        with self.assertRaises(ValidationError):
            self.es_check.full_clean()

    @patch('cabot.metricsapp.models.elastic.MultiSearch.execute', empty_es_response)
    @patch('time.time', mock_time)
    def test_empty_response(self):
        """Test result when elasticsearch returns an empty response"""
        series = self.es_check.get_series()
        self.assertTrue(series['error'])

        result = self.es_check._run()
        self.assertFalse(result.succeeded)
        self.assertEqual(result.error, 'Error fetching metric from source')

    @patch('cabot.metricsapp.models.elastic.MultiSearch.execute', fake_es_multiple_metrics_terms)
    @patch('time.time', mock_time)
    def test_terms_aggregation(self):
        self.es_check.check_type = '<'
        self.es_check.warning_value = 15
        self.es_check.high_alert_value = 18
        series = self.es_check.get_series()
        self.assertFalse(series['error'])
        self.assertEqual(series['raw'], get_json_file('es_multiple_metrics_terms.json'))

        data = series['data']
        self.assertEqual(len(data), 4)

        # Sort to make sure the order is always the same
        data = sorted(data, key=lambda d: d['series'])

        self.assertEqual(str(data[0]['series']), 'gold.max')
        self.assertEqual(data[0]['datapoints'], [[1491566400, 12.220], [1491570000, 14.490],
                                                 [1491573600, 14.400]])
        self.assertEqual(str(data[1]['series']), 'gold.min')
        self.assertEqual(data[1]['datapoints'], [[1491566400, 12.221], [1491570000, 14.491],
                                                 [1491573600, 14.401]])
        self.assertEqual(str(data[2]['series']), 'maroon.max')
        self.assertEqual(data[2]['datapoints'], [[1491566400, 17.602], [1491570000, 15.953],
                                                 [1491573600, 18.296]])
        self.assertEqual(str(data[3]['series']), 'maroon.min')
        self.assertEqual(data[3]['datapoints'], [[1491566400, 17.603], [1491570000, 15.954],
                                                 [1491573600, 17.297]])

        # Test check result
        result = self.es_check._run()
        self.assertFalse(result.succeeded)
        self.assertEquals(result.error, 'maroon.max: 18.3 < 18.0')
        self.assertEqual(self.es_check.importance, Service.CRITICAL_STATUS)

    @patch('cabot.metricsapp.models.elastic.MultiSearch.execute', fake_es_percentile)
    @patch('time.time', mock_time)
    def test_percentile(self):
        series = self.es_check.get_series()
        self.assertFalse(series['error'])
        self.assertEqual(series['raw'], get_json_file('es_percentile.json'))

        data = series['data']
        self.assertEqual(len(data), 3)

        # Sort to make sure the order will always be the same
        data = sorted(data, key=lambda d: d['series'])

        self.assertEqual(str(data[0]['series']), '25.0')
        self.assertEqual(data[0]['datapoints'], [[1491566400, 294.75], [1491570000, 377.125],
                                                 [1491573600, 403.0]])
        self.assertEqual(str(data[1]['series']), '50.0')
        self.assertEqual(data[1]['datapoints'], [[1491566400, 1120.0], [1491570000, 1124.0],
                                                 [1491573600, 1138.3333333333333]])
        self.assertEqual(str(data[2]['series']), '75.0')
        self.assertEqual(data[2]['datapoints'], [[1491566400, 1350.0], [1491570000, 1299.0833333333333],
                                                 [1491573600, 1321.875]])

    @patch('cabot.metricsapp.models.elastic.MultiSearch.execute', fake_es_multiple_terms)
    @patch('time.time', mock_time)
    def test_multiple_terms(self):
        series = self.es_check.get_series()
        self.assertFalse(series['error'])
        self.assertEqual(series['raw'], get_json_file('es_multiple_terms.json'))

        data = series['data']
        self.assertEqual(len(data), 3)

        # Sort to make sure the order will always be the same
        data = sorted(data, key=lambda d: d['series'])

        self.assertEqual(str(data[0]['series']), 'north.east.min')
        self.assertEqual(data[0]['datapoints'], [[1491566400, 19.0]])
        self.assertEqual(str(data[1]['series']), 'north.west.min')
        self.assertEqual(data[1]['datapoints'], [[1491566400, 15.0]])
        self.assertEqual(str(data[2]['series']), 'south.west.min')
        self.assertEqual(data[2]['datapoints'], [[1491566400, 16.0]])

    @patch('cabot.metricsapp.models.elastic.MultiSearch.execute', fake_es_response)
    @patch('time.time', mock_time)
    def test_time_range(self):
        """Should not return data earlier than now - the time range"""
        self.es_check.time_range = 90

        series = self.es_check.get_series()
        self.assertFalse(series['error'])
        self.assertEqual(series['raw'], get_json_file('es_response.json'))
        data = series['data']
        self.assertEqual(len(data), 1)

        data = data[0]
        self.assertEqual(str(data['series']), 'avg')
        self.assertEqual(data['datapoints'], [[1491573600, 4.4642857142857]])

    @patch('cabot.metricsapp.models.elastic.MultiSearch.execute', fake_es_multiple_queries)
    @patch('time.time', mock_time)
    def test_multiple_queries(self):
        series = self.es_check.get_series()
        self.assertFalse(series['error'])
        self.assertEqual(series['raw'], get_json_file('es_response.json') + get_json_file('es_percentile.json'))

        data = series['data']
        # 1 from es_response, 3 from es_percentile
        self.assertEqual(len(data), 4)

        # Sort to make sure the order is always the same
        data = sorted(data, key=lambda d: d['series'])

        self.assertEqual(str(data[0]['series']), '25.0')
        self.assertEqual(data[0]['datapoints'], [[1491566400, 294.75], [1491570000, 377.125],
                                                 [1491573600, 403.0]])
        self.assertEqual(str(data[1]['series']), '50.0')
        self.assertEqual(data[1]['datapoints'], [[1491566400, 1120.0], [1491570000, 1124.0],
                                                 [1491573600, 1138.3333333333333]])
        self.assertEqual(str(data[2]['series']), '75.0')
        self.assertEqual(data[2]['datapoints'], [[1491566400, 1350.0], [1491570000, 1299.0833333333333],
                                                 [1491573600, 1321.875]])
        self.assertEqual(str(data[3]['series']), 'avg')
        self.assertEqual(data[3]['datapoints'], [[1491552000, 4.9238095238095], [1491555600, 4.7958115183246],
                                                 [1491559200, 3.53005464480873], [1491562800, 4.04651162790697],
                                                 [1491566400, 4.8390501319261], [1491570000, 4.51913477537437],
                                                 [1491573600, 4.4642857142857]])

    @patch('cabot.metricsapp.models.elastic.MultiSearch.execute', fake_es_none)
    @patch('time.time', mock_time)
    def test_none(self):
        # Test output series
        series = self.es_check.get_series()
        self.assertFalse(series['error'])
        self.assertEqual(series['raw'], get_json_file('es_none_nan.json'))
        data = series['data']
        self.assertEqual(len(data), 1)

        data = data[0]
        self.assertEqual(str(data['series']), 'avg')
        self.assertEqual(data['datapoints'], [[1491555600, 4.7958115183246], [1491562800, 4.04651162790697],
                                              [1491570000, 4.51913477537437], [1491573600, 4.4642857142857]])

        # Test check result
        result = self.es_check._run()
        self.assertTrue(result.succeeded)
        self.assertIsNone(result.error)


class TestQueryValidation(TestCase):
    def test_valid_query(self):
        query = '{"aggs": {"agg": {"terms": {"field": "a1"},' \
                '"aggs": {"agg": {"terms": {"field": "b2"},' \
                '"aggs": {"agg": {"date_histogram": {"field": "@timestamp","interval": "hour"},' \
                '"aggs": {"max": {"max": {"field": "timing"}}}}}}}}}}'
        # Should not throw an exception
        validate_query(json.loads(query))

    def test_not_agg(self):
        """Aggregations must be named 'agg'"""
        query = '{"aggs": {"notagg": {"terms": {"field": "data"},' \
                '"aggs": {"agg": {"date_histogram": {"field": "@timestamp","interval": "hour"},' \
                '"aggs": {"max": {"max": {"field": "timing"}}}}}}}}'

        with self.assertRaises(ValidationError) as e:
            validate_query(json.loads(query))
            self.assertEqual(e.exception, '{}: aggregations should be named "agg."'.format(ES_VALIDATION_MSG_PREFIX))

    def test_external_date_hist(self):
        """date_histogram must be the innermost aggregation"""
        query = '{"aggs": {"agg": {"date_histogram": {"field": "@timestamp","interval": "hour"},' \
                '"aggs": {"agg": {"terms": {"field": "data"},' \
                '"aggs": {"max": {"max": {"field": "timing"}}}}}}}}'

        with self.assertRaises(ValidationError) as e:
            validate_query(json.loads(query))
            self.assertEqual(e.exception, '{}: date_histogram must be the innermost aggregation (besides metrics).'
                             .format(ES_VALIDATION_MSG_PREFIX))

    def test_unsupported_metric(self):
        query = '{"aggs": {"agg": {"terms": {"field": "data"},' \
                '"aggs": {"agg": {"date_histogram": {"field": "@timestamp","interval": "hour"},' \
                '"aggs": {"raw_document": {"max": {"field": "timing"}}}}}}}}'

        with self.assertRaises(ValidationError) as e:
            validate_query(json.loads(query))
            self.assertEqual(e.exception, '{}: unsupported metric "raw_document."'.format(ES_VALIDATION_MSG_PREFIX))

    def test_nonmatching_metric_name(self):
        query = '{"aggs": {"agg": {"terms": {"field": "data"},' \
                '"aggs": {"agg": {"date_histogram": {"field": "@timestamp","interval": "hour"},' \
                '"aggs": {"min": {"max": {"field": "timing"}}}}}}}}'

        with self.assertRaises(ValidationError) as e:
            validate_query(json.loads(query))
            self.assertEqual(e.exception, '{}: metric name must be the same as the metric type.'
                             .format(ES_VALIDATION_MSG_PREFIX))

    def test_no_date_histogram(self):
        query = '{"aggs": {"agg": {"terms": {"field": "no"},' \
                '"aggs": {"agg": {"terms": {"field": "data"},' \
                '"aggs": {"max": {"max": {"field": "timing"}}}}}}}}'

        with self.assertRaises(ValidationError) as e:
            validate_query(json.loads(query))
            self.assertEqual(e.exception, '{}: query must at least include a date_histogram aggregation.'
                             .format(ES_VALIDATION_MSG_PREFIX))
