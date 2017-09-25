from django.core.exceptions import ValidationError
from django.test import TestCase
from cabot.metricsapp.api import build_query, template_response, validate_query, \
    create_elasticsearch_templating_dict, get_es_status_check_fields, adjust_time_range
from .test_elasticsearch import get_json_file


class TestGrafanaQueryBuilder(TestCase):
    def test_grafana_query(self):
        """Basic query building"""
        series = get_json_file('grafana/query_builder/grafana_series.json')
        created_query = build_query(series, min_time='now-1h')
        expected_query = get_json_file('grafana/query_builder/grafana_series_query.json')
        self.assertEqual(expected_query, created_query)
        validate_query(created_query)

    def test_multiple_aggs(self):
        """Multiple terms aggregations"""
        series = get_json_file('grafana/query_builder/grafana_series_terms.json')
        created_query = build_query(series, min_time='now-100m')
        expected_query = get_json_file('grafana/query_builder/grafana_series_terms_query.json')
        self.assertEqual(expected_query, created_query)
        validate_query(created_query)

    def test_order_by_sub_agg(self):
        """Order by sub-aggregations"""
        series = get_json_file('grafana/query_builder/grafana_series_order_sub_agg.json')
        created_query = build_query(series, min_time='now-100m')
        expected_query = get_json_file('grafana/query_builder/grafana_series_order_sub_agg_query.json')
        self.assertEqual(expected_query, created_query)
        validate_query(created_query)

    def test_count(self):
        """Count metrics get converted to value_count(timeField)"""
        series = get_json_file('grafana/query_builder/grafana_series_count.json')
        created_query = build_query(series, min_time='now-3d')
        expected_query = get_json_file('grafana/query_builder/grafana_series_count_query.json')
        self.assertEqual(expected_query, created_query)
        validate_query(created_query)

    def test_multiple_metrics(self):
        """Multiple metrics (for example, sum and avg)"""
        series = get_json_file('grafana/query_builder/grafana_multiple_metrics.json')
        created_query = build_query(series, min_time='now-30m')
        expected_query = get_json_file('grafana/query_builder/grafana_multiple_metrics_query.json')
        self.assertEqual(expected_query, created_query)
        validate_query(created_query)

    def test_derivative(self):
        """Derivative metric with hidden field"""
        series = get_json_file('grafana/query_builder/grafana_derivative.json')
        created_query = build_query(series, min_time='now-3h')
        expected_query = get_json_file('grafana/query_builder/grafana_derivative_query.json')
        self.assertEqual(expected_query, created_query)
        validate_query(created_query)

    def test_histogram_agg(self):
        """histogram aggregation"""
        series = get_json_file('grafana/query_builder/grafana_histogram_agg.json')
        created_query = build_query(series, min_time='now-1h')
        expected_query = get_json_file('grafana/query_builder/grafana_histogram_agg_query.json')
        self.assertEqual(expected_query, created_query)
        validate_query(expected_query)

    def test_filters_agg(self):
        """filter aggregation"""
        series = get_json_file('grafana/query_builder/grafana_filters_agg.json')
        created_query = build_query(series, min_time='now-1h')
        expected_query = get_json_file('grafana/query_builder/grafana_filters_agg_query.json')
        self.assertEqual(expected_query, created_query)
        validate_query(expected_query)

    def test_no_date_histogram(self):
        """If there's no date_histogram agg, raise an exception"""
        series = get_json_file('grafana/query_builder/grafana_no_date_histogram.json')
        with self.assertRaises(ValidationError) as e:
            build_query(series, min_time='now-30m')
            self.assertEqual(e.exception, 'Dashboard must include a date histogram aggregation.')

    def test_unsupported_aggregation(self):
        """Exceptions raised for aggs that aren't supported"""
        series = get_json_file('grafana/query_builder/grafana_geo_hash_grid.json')
        with self.assertRaises(ValidationError) as e:
            build_query(series, min_time='now-30m')
            self.assertEqual(e.exception, 'geohash_grid aggregation not supported.')

    def test_get_es_status_check_fields(self):
        dashboard_info = get_json_file('../grafana/dashboard_detail_response.json')

        status_check_fields = []
        for row in dashboard_info['dashboard']['rows']:
            for panel in row['panels']:
                status_check_fields.append(get_es_status_check_fields(dashboard_info, panel, ['B']))

        expected_queries = get_json_file('grafana/query_builder/get_es_status_check_fields_queries.json')
        expected_fields = [dict(queries=expected_queries[0])]
        # Second panel doesn't have a 'B' series
        expected_fields.append(dict())
        expected_fields.append(dict(queries=expected_queries[1]))

        self.assertEqual(status_check_fields, expected_fields)

    def test_adjust_time_range(self):
        queries = [get_json_file('grafana/query_builder/grafana_series_query.json')]
        new_queries = adjust_time_range(queries, 30)
        expected_queries = [get_json_file('grafana/query_builder/grafana_series_query_30m.json')]
        self.assertEqual(new_queries, expected_queries)


class TestGrafanaTemplating(TestCase):
    def test_templating(self):
        """Test Grafana panel templating handling"""
        templates = get_json_file('grafana/templating/templating_info.json')
        templating_dict = create_elasticsearch_templating_dict(templates)

        panel_info = get_json_file('grafana/templating/templating_panel.json')
        expected_panel = get_json_file('grafana/templating/templating_panel_final.json')

        templated_panel = template_response(panel_info, templating_dict)
        self.assertEqual(templated_panel, expected_panel)

        # Make sure we can make a valid query from the output
        query = build_query(templated_panel, min_time='now-1h')
        validate_query(query)

    def test_auto_time_field(self):
        """Make sure 'auto' fields are getting templated correctly"""
        templates = get_json_file('grafana/templating/auto_time_templating.json')
        templating_dict = create_elasticsearch_templating_dict(templates)

        panel = get_json_file('grafana/templating/auto_time_panel.json')
        templated_panel = template_response(panel, templating_dict)

        created_query = build_query(templated_panel, default_interval='2m')
        expected_query = get_json_file('grafana/templating/auto_time_panel_query.json')
        self.assertEqual(expected_query, created_query)
        validate_query(created_query)
