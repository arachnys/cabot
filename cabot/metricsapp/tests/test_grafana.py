import json
import os
from django.test import TestCase
from mock import patch
from cabot.metricsapp.api import get_dashboard_choices, get_panel_choices, create_generic_templating_dict, \
    get_series_choices, get_status_check_fields
from cabot.metricsapp.models import GrafanaInstance


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
        status_check_fields = []
        for row in self.dashboard_info['dashboard']['rows']:
            for panel in row['panels']:
                status_check_fields.append(get_status_check_fields(self.dashboard_info, panel, 1, 'datasource',
                                                                   self.templating_dict))

        expected_fields = [
            dict(name='42',
                 source_info=dict(grafana_source_name='datasource', grafana_instance_id=1),
                 time_range=180,
                 high_alert_value=1.0,
                 check_type='>',
                 warning_value=0.0),
            dict(name='Pct 75',
                 source_info=dict(grafana_source_name='datasource', grafana_instance_id=1),
                 time_range=180,
                 warning_value=100.0,
                 check_type='<'),
            dict(name='Panel 106',
                 source_info=dict(grafana_source_name='datasource', grafana_instance_id=1),
                 time_range=180)
        ]

        self.assertEqual(status_check_fields, expected_fields)


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
