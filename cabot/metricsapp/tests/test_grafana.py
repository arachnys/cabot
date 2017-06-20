import json
import os
from datetime import datetime
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from mock import patch, Mock
from cabot.metricsapp.api import get_dashboard_choices, get_panel_choices, create_generic_templating_dict, \
    get_series_choices, get_status_check_fields, get_panel_url, get_series_ids, get_updated_datetime, get_panel_info
from cabot.metricsapp.models import ElasticsearchStatusCheck, ElasticsearchSource, GrafanaDataSource, \
    GrafanaInstance, GrafanaPanel
from cabot.metricsapp.tasks import sync_grafana_check, sync_all_grafana_checks


def get_json_file(file):
    path = os.path.join(os.path.dirname(__file__), 'fixtures/grafana/{}'.format(file))
    with open(path) as f:
        return json.loads(f.read())


class TestGrafanaApiParsing(TestCase):
    def setUp(self):
        self.dashboard_list = get_json_file('dashboard_list_response.json')
        self.dashboard_info = get_json_file('dashboard_detail_response.json')
        self.templating_dict = create_generic_templating_dict(self.dashboard_info)

    def test_get_dashboard_choices(self):
        choices = get_dashboard_choices(self.dashboard_list)

        expected_choices = [('db/awesome-dashboard', 'Awesome Dashboard'),
                            ('db/really-really-good-dashboard', 'Really Really Good Dashboard'),
                            ('db/also-great-dashboard', 'Also Great Dashboard'),
                            ('db/only-ok-dashboard', 'Only Ok Dashboard')]

        self.assertEqual(choices, expected_choices)

    def test_get_panel_choices(self):
        choices = get_panel_choices(self.dashboard_info, self.templating_dict)
        # Remove extended panel data from choices
        choices = [(dict(panel_id=panel[0]['panel_id'], datasource=panel[0]['datasource']),
                    panel[1]) for panel in choices]

        # ({id, datasource}, title)
        expected_choices = [(dict(panel_id=1, datasource='deep-thought'), '42'),
                            (dict(panel_id=5, datasource='shallow-thought'), 'Pct 75'),
                            (dict(panel_id=3, datasource='ds'), 'Panel 106')]

        self.assertEqual(choices, expected_choices)

    def test_get_series_choices(self):
        series_choices = []
        for row in self.dashboard_info['dashboard']['rows']:
            for panel in row['panels']:
                series = get_series_choices(panel, self.templating_dict)
                series_choices.append([(s[0], json.loads(s[1])) for s in series])

        expected_series_choices = [
            [(u'B', dict(alias='42',
                         bucketAggs=[dict(field='@timestamp',
                                          id='2',
                                          settings=dict(interval='1m', min_doc_count=0, trimEdges=0),
                                          type='date_histogram')],
                         metrics=[dict(field='value',
                                       id='1',
                                       meta={},
                                       settings={},
                                       type='sum')],
                         query='query:life-the-universe-and-everything'))],
            [(u'A', dict(alias='al',
                         bucketAggs=[dict(fake=True,
                                          field='@timestamp',
                                          id='3',
                                          settings=dict(interval='1m', min_doc_count=0, trimEdges=0),
                                          type='date_histogram')],
                         metrics=[dict(field='count',
                                       id='1',
                                       meta={},
                                       settings={},
                                       type='sum')],
                         query='query:who-cares'))],
            [(u'B', dict(bucketAggs=[dict(fake=True,
                                          field='wrigley',
                                          id='3',
                                          settings=dict(min_doc_count=1, size='20'),
                                          type='terms'),
                                     dict(field='@timestamp',
                                          id='2',
                                          settings=dict(interval='1m', min_doc_count=0, trimEdges=0),
                                          type='date_histogram')],
                         metrics=[dict(field='timing',
                                       id='1',
                                       meta={},
                                       settings=dict(percents=['75']),
                                       type='percentiles')],
                         query='name:the-goat AND module:module'))]
        ]

        self.assertEqual(series_choices, expected_series_choices)

    def test_get_status_check_fields(self):
        grafana_data_source = Mock()
        grafana_data_source.metrics_source_base = 'datasource'

        status_check_fields = []
        for row in self.dashboard_info['dashboard']['rows']:
            for panel in row['panels']:
                status_check_fields.append(get_status_check_fields(self.dashboard_info, panel, grafana_data_source,
                                                                   self.templating_dict, 1))

        expected_fields = [
            dict(name='42',
                 source='datasource',
                 time_range=180,
                 high_alert_value=1.0,
                 check_type='>',
                 grafana_panel=1,
                 warning_value=0.0),
            dict(name='Pct 75',
                 source='datasource',
                 time_range=180,
                 warning_value=100.0,
                 grafana_panel=1,
                 check_type='<'),
            dict(name='Panel 106',
                 source='datasource',
                 grafana_panel=1,
                 time_range=180)
        ]

        self.assertEqual(status_check_fields, expected_fields)

    def test_get_series_ids(self):
        series1 = get_series_ids(get_panel_info(self.dashboard_info, 1))
        self.assertEqual(series1, 'B')

        series5 = get_series_ids(get_panel_info(self.dashboard_info, 5))
        self.assertEqual(series5, 'A')

        series3 = get_series_ids(get_panel_info(self.dashboard_info, 3))
        self.assertEqual(series3, 'B')

    def test_get_updated_datetime(self):
        time = get_updated_datetime(self.dashboard_info)
        self.assertEqual(time, datetime(2017, 2, 1, 0, 0, 0))


class TestGrafanaApiRequests(TestCase):
    def setUp(self):
        self.grafana_instance = GrafanaInstance.objects.create(
            name='test',
            url='http://test.url',
            api_key='88888'
        )

    def test_auth_header(self):
        self.assertTrue(self.grafana_instance.session.headers['Authorization'] == 'Bearer 88888')

    @patch('cabot.metricsapp.models.grafana.requests.Session.get')
    def test_get_request(self, fake_get):
        self.grafana_instance.get_request('index.html')
        fake_get.assert_called_once_with('http://test.url/index.html')


class TestPanelUrl(TestCase):
    def test_panel_url_creation(self):
        dashboard_info = get_json_file('dashboard_detail_response.json')
        templating_dict = create_generic_templating_dict(dashboard_info)

        panel_url = get_panel_url('https://grafana-site.com', 'db/dddashboard', 1, templating_dict)

        self.assertEqual(panel_url, 'https://grafana-site.com/dashboard-solo/db/dddashboard?panelId=1'
                                    '&var-percentile_1=75&var-group_by=1m&var-module=module')


def fake_get_dashboard_info(*args):
    return get_json_file('dashboard_detail_response.json')


def raise_validation_error(*args):
    raise ValidationError('you did bad')


class TestDashboardSync(TestCase):
    def setUp(self):
        self.source = ElasticsearchSource.objects.create(
            name='hi',
            urls='localhost'
        )
        self.grafana_instance = GrafanaInstance.objects.create(
            name='graf',
            url='graf',
            api_key='graf'
        )
        self.grafana_data_source = GrafanaDataSource.objects.create(
            grafana_source_name='deep-thought',
            grafana_instance=self.grafana_instance,
            metrics_source_base=self.source
        )
        user = User.objects.create_user('hi', email='hi@affirm.com')
        User.objects.create_user('admin', email='admin@affirm.com')
        User.objects.create_user('user', email='enduser@affirm.com')
        self.panel = GrafanaPanel.objects.create(
            grafana_instance=self.grafana_instance,
            panel_id=1,
            dashboard_uri='db/42',
            series_ids='B',
            selected_series='B'
        )
        self.queries = json.dumps([{'query': {'bool': {'must': [{'query_string':
                                                                     {'analyze_wildcard': True,
                                                                      'query':
                                                                          u'query:life-the-universe-and-everything'}},
                                                                {'range': {u'@timestamp': {'gte': u'now-3h'}}}]}},
                                    'aggs': {'agg': {'date_histogram': {'field': u'@timestamp', 'interval': u'1m',
                                                                        'extended_bounds':
                                                                            {'max': 'now', 'min': u'now-3h'}},
                                                     'aggs': {u'sum': {'sum': {'field': u'value'}}}}}}])
        self.check = ElasticsearchStatusCheck.objects.create(
            name='42',
            created_by=user,
            source=self.source,
            check_type='>',
            warning_value=0,
            high_alert_importance='ERROR',
            high_alert_value=1,
            queries=self.queries,
            time_range=180,
            grafana_panel=self.panel,
            auto_sync=True
        )

    @patch('cabot.metricsapp.tasks.get_dashboard_info', fake_get_dashboard_info)
    @patch('cabot.metricsapp.tasks.send_grafana_sync_email.apply_async')
    def test_dashboard_not_updated_time(self, send_email):
        sync_grafana_check(self.check.id, str(datetime(2017, 3, 1, 0, 0, 0, 1231)))
        # No emails should be sent since it hasn't been updated recently
        self.assertFalse(send_email.called)

    @patch('cabot.metricsapp.tasks.get_dashboard_info', fake_get_dashboard_info)
    @patch('cabot.metricsapp.tasks.send_grafana_sync_email.apply_async')
    def test_dashboard_no_changes(self, send_email):
        sync_grafana_check(self.check.id, str(datetime(2017, 2, 1, 0, 0, 1, 123)))
        # No emails should be sent since nothing relevant in the dashboard has changed
        self.assertFalse(send_email.called)

    @patch('cabot.metricsapp.tasks.get_dashboard_info', fake_get_dashboard_info)
    @patch('cabot.metricsapp.tasks.sync_grafana_check.apply_async')
    def test_no_grafana_panel(self, sync_check):
        """We don't check checks without associated Grafana panels"""
        self.check.grafana_panel = None
        self.check.save()
        sync_all_grafana_checks()
        self.assertFalse(sync_check.called)

    @patch('cabot.metricsapp.tasks.get_dashboard_info', fake_get_dashboard_info)
    @patch('cabot.metricsapp.tasks.send_grafana_sync_email.apply_async')
    def test_change_panel_name(self, send_email):
        self.check.name = '44'
        self.check.save()

        sync_grafana_check(self.check.id, str(datetime(2017, 2, 1, 0, 0, 1, 1231)))
        send_email.assert_called_once_with(args=(['hi@affirm.com', 'admin@affirm.com', 'enduser@affirm.com'],
                                                 'http://localhost/check/{}/\n\n'
                                                 'The check name has changed from "44" to "42".'.format(self.check.id),
                                                 '44'))
        self.assertEqual(ElasticsearchStatusCheck.objects.get(id=self.check.id).name, '42')

    @patch('cabot.metricsapp.tasks.get_dashboard_info', fake_get_dashboard_info)
    @patch('cabot.metricsapp.tasks.send_grafana_sync_email.apply_async')
    def test_change_datasource(self, send_email):
        self.grafana_data_source.grafana_source_name = 'hello'
        self.grafana_data_source.save()

        sync_grafana_check(self.check.id, str(datetime(2017, 2, 1, 0, 0, 1, 231)))
        send_email.assert_called_once_with(args=(['hi@affirm.com', 'admin@affirm.com', 'enduser@affirm.com'],
                                                 'http://localhost/check/{}/\n\n'
                                                 'The Grafana data source has changed from "hello" to "deep-thought". '
                                                 'The new source is not configured in Cabot, so the status check will '
                                                 'continue to use the old source.'.format(self.check.id), '42'))

    @patch('cabot.metricsapp.tasks.get_dashboard_info', fake_get_dashboard_info)
    @patch('cabot.metricsapp.tasks.send_grafana_sync_email.apply_async')
    def test_change_series_ids(self, send_email):
        self.panel.series_ids = 'B,E'
        self.panel.save()

        sync_grafana_check(self.check.id, str(datetime(2017, 2, 1, 0, 0, 1, 12)))
        send_email.assert_called_once_with(args=(['hi@affirm.com', 'admin@affirm.com', 'enduser@affirm.com'],
                                                 'http://localhost/check/{}/\n\n'
                                                 'The panel series ids have changed from B,E to B. The check has not '
                                                 'been changed.'.format(self.check.id), '42'))
        self.assertEqual(GrafanaPanel.objects.get(id=self.panel.id).series_ids, 'B')

    @patch('cabot.metricsapp.tasks.get_dashboard_info', fake_get_dashboard_info)
    @patch('cabot.metricsapp.tasks.send_grafana_sync_email.apply_async')
    def test_change_queries(self, send_email):
        self.check.queries = 'to-be-or-not-to-be'
        self.check.save()

        sync_grafana_check(self.check.id, str(datetime(2017, 2, 1, 0, 0, 1, 123)))
        send_email.assert_called_once_with(args=(['hi@affirm.com', 'admin@affirm.com', 'enduser@affirm.com'],
                                                 'http://localhost/check/{}/\n\n'
                                                 'The queries have changed from\nto-be-or-not-to-be\nto\n{}.'.format(
                                                     self.check.id, str(self.queries)
                                                 ), '42'))
        self.assertEqual(ElasticsearchStatusCheck.objects.get(id=self.check.id).queries, str(self.queries))

    @patch('cabot.metricsapp.tasks.get_dashboard_info', fake_get_dashboard_info)
    @patch('cabot.metricsapp.tasks.send_grafana_sync_email.apply_async')
    def test_change_multiple(self, send_email):
        self.check.name = 'goodbye'
        self.check.queries = 'to-be-or-not-to-be'
        self.check.save()

        sync_grafana_check(self.check.id, str(datetime(2017, 2, 1, 0, 0, 1, 12312)))
        send_email.assert_called_once_with(args=(['hi@affirm.com', 'admin@affirm.com', 'enduser@affirm.com'],
                                                 'http://localhost/check/{}/\n\n'
                                                 'The check name has changed from "goodbye" to "42".\n\n'
                                                 'The queries have changed from\nto-be-or-not-to-be\nto\n{}.'.format(
                                                     self.check.id, str(self.queries)
                                                 ), 'goodbye'))
        check = ElasticsearchStatusCheck.objects.get(id=self.check.id)
        self.assertEqual(check.name, '42')
        self.assertEqual(check.queries, str(self.queries))

    @patch('cabot.metricsapp.tasks.get_dashboard_info', raise_validation_error)
    @patch('cabot.metricsapp.tasks.send_grafana_sync_email.apply_async')
    def test_dashboard_deleted(self, send_email):
        sync_grafana_check(self.check.id, str(datetime(2017, 2, 1, 0, 0, 1, 1231)))
        send_email.assert_called_once_with(args=(['hi@affirm.com'],
                                                 'http://localhost/check/{}/\n\n'
                                                 'Dashboard "{}" has been deleted, so check "{}" has been '
                                                 'deactivated. If you would like to keep the check, re-enable it '
                                                 'with auto_sync: False.'
                                                 .format(self.check.id, '42', '42'),
                                                 '42'))
        check = ElasticsearchStatusCheck.objects.get(id=self.check.id)
        self.assertFalse(check.active)

    @patch('cabot.metricsapp.tasks.get_dashboard_info', fake_get_dashboard_info)
    @patch('cabot.metricsapp.tasks.get_panel_info', raise_validation_error)
    @patch('cabot.metricsapp.tasks.send_grafana_sync_email.apply_async')
    def test_panel_deleted(self, send_email):
        sync_grafana_check(self.check.id, str(datetime(2017, 2, 1, 0, 0, 1, 12321)))
        send_email.assert_called_once_with(args=(['hi@affirm.com', 'admin@affirm.com', 'enduser@affirm.com'],
                                                 'http://localhost/check/{}/\n\n'
                                                 'Panel {} in dashboard "{}" has been deleted, so check "{}" has been '
                                                 'deactivated. If you would like to keep the check, re-enable it with '
                                                 'auto_sync: False.'.format(self.check.id, '1', '42', '42'),
                                                 '42'))

        check = ElasticsearchStatusCheck.objects.get(id=self.check.id)
        self.assertFalse(check.active)
