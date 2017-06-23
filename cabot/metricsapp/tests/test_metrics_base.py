from django.contrib.auth.models import User
from django.test import TestCase
from mock import patch
import os
import yaml
from cabot.cabotapp.models import Service
from cabot.metricsapp.models import MetricsStatusCheckBase, MetricsSourceBase


def get_content(filename):
    path = os.path.join(os.path.dirname(__file__), 'fixtures/%s' % filename)
    with open(path) as f:
        return f.read()


def mock_get_series(*args):
    return yaml.load(get_content('metrics_series.yaml'))


def get_series_error(*args):
    return yaml.load(get_content('metrics_error.yaml'))


def mock_time():
    return 1387817760.0


class TestMetricsBase(TestCase):
    """Test cases for _run() in MetricsStatusCheckBase"""
    def setUp(self):
        self.user = User.objects.create_user('user')
        self.source = MetricsSourceBase.objects.create(name='source')
        self.metrics_check = MetricsStatusCheckBase(
            name='test',
            created_by=self.user,
            source=self.source,
            check_type='<=',
            warning_value=9.0,
        )

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_failure(self):
        result = self.metrics_check._run()
        self.assertEqual(result.check, self.metrics_check)
        self.assertFalse(result.succeeded)
        self.assertEqual(result.error, u'prod.good.data: 9.2 <= 9.0')

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_success(self):
        self.metrics_check.warning_value = 10.0
        result = self.metrics_check._run()
        self.assertEqual(result.check, self.metrics_check)
        self.assertTrue(result.succeeded)
        self.assertIsNone(result.error)

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_lte(self):
        # maximum value in the series
        self.metrics_check.warning_value = 9.66092
        self.metrics_check.save()
        result = self.metrics_check._run()
        self.assertTrue(result.succeeded)

        self.metrics_check.warning_value = 9.66091
        self.metrics_check.save()
        result = self.metrics_check._run()
        self.assertFalse(result.succeeded)

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_lt(self):
        self.metrics_check.check_type = '<'
        # maximum value in the series
        self.metrics_check.warning_value = 9.66092
        self.metrics_check.save()
        result = self.metrics_check._run()
        self.assertFalse(result.succeeded)

        self.metrics_check.warning_value = 9.660921
        self.metrics_check.save()
        result = self.metrics_check._run()
        self.assertTrue(result.succeeded)

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_gte(self):
        self.metrics_check.check_type = '>='
        # minimum value in the series
        self.metrics_check.warning_value = 1.16092
        self.metrics_check.save()
        result = self.metrics_check._run()
        self.assertTrue(result.succeeded)

        self.metrics_check.warning_value = 1.16093
        self.metrics_check.save()
        result = self.metrics_check._run()
        self.assertFalse(result.succeeded)

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_gt(self):
        self.metrics_check.check_type = '>'
        # minimum value in the series
        self.metrics_check.warning_value = 1.16092
        self.metrics_check.save()
        result = self.metrics_check._run()
        self.assertFalse(result.succeeded)

        self.metrics_check.warning_value = 1.160915
        self.metrics_check.save()
        result = self.metrics_check._run()
        self.assertTrue(result.succeeded)

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    def test_no_datapoints(self):
        """
        Run check at the current time (all the points are outdated). Should succeed
        """
        result = self.metrics_check._run()
        self.assertEqual(result.check, self.metrics_check)
        self.assertTrue(result.succeeded)
        self.assertIsNone(result.error)

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', get_series_error)
    def test_error(self):
        result = self.metrics_check._run()
        self.assertEqual(result.check, self.metrics_check)
        self.assertFalse(result.succeeded)
        self.assertEqual(result.error, 'Error fetching metric from source')

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    def test_raw_data(self):
        result = self.metrics_check._run()
        series = mock_get_series()
        threshold = {'series': 'alert.warning_threshold', 'datapoints': [[1387817760, 9.0], [1387818600, 9.0]]}
        series['data'].append(threshold)
        self.assertEqual(eval(result.raw_data), series['data'])


class TestMultipleThresholds(TestCase):
    """Test cases relating to multiple alert thresholds"""
    def setUp(self):
        self.user = User.objects.create_user('user')
        self.source = MetricsSourceBase.objects.create(name='source')
        self.metrics_check = MetricsStatusCheckBase(
            name='multi',
            created_by=self.user,
            source=self.source,
            check_type='<=',
            warning_value=9.0,
            high_alert_value=11.0,
            high_alert_importance=Service.CRITICAL_STATUS
        )

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_warning(self):
        """Test cases with both high alert and warning values"""
        result = self.metrics_check._run()
        self.assertFalse(result.succeeded)
        self.assertEqual(result.error, u'prod.good.data: 9.2 <= 9.0')
        self.assertEqual(self.metrics_check.importance, Service.WARNING_STATUS)

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_critical(self):
        self.metrics_check.high_alert_value = 9.5
        result = self.metrics_check._run()
        self.assertFalse(result.succeeded)
        self.assertEqual(result.error, u'prod.good.data: 9.7 <= 9.5')
        self.assertEqual(self.metrics_check.importance, Service.CRITICAL_STATUS)

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_error(self):
        self.metrics_check.high_alert_value = 9.5
        self.metrics_check.high_alert_importance = Service.ERROR_STATUS
        result = self.metrics_check._run()
        self.assertFalse(result.succeeded)
        self.assertEqual(result.error, u'prod.good.data: 9.7 <= 9.5')
        self.assertEqual(self.metrics_check.importance, Service.ERROR_STATUS)

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_success(self):
        self.metrics_check.warning_value = 10.0
        result = self.metrics_check._run()
        self.assertTrue(result.succeeded)
        self.assertIsNone(result.error)

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_multiple_thresholds(self):
        result = self.metrics_check._run()
        series = mock_get_series()

        warning_threshold = {'series': 'alert.warning_threshold',
                             'datapoints': [[1387817760, 9.0], [1387818600, 9.0]]}
        series['data'].append(warning_threshold)
        critical_threshold = {'series': 'alert.high_alert_threshold',
                              'datapoints': [[1387817760, 11.0], [1387818600, 11.0]]}
        series['data'].append(critical_threshold)
        self.assertEqual(eval(result.raw_data), series['data'])

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_warning_only(self):
        """Check only has a warning value"""
        self.metrics_check.high_alert_value = None
        result = self.metrics_check._run()
        self.assertEqual(result.check, self.metrics_check)
        self.assertFalse(result.succeeded)
        self.assertEqual(result.error, u'prod.good.data: 9.2 <= 9.0')
        self.assertEqual(self.metrics_check.importance, Service.WARNING_STATUS)

    @patch('cabot.metricsapp.models.MetricsStatusCheckBase.get_series', mock_get_series)
    @patch('time.time', mock_time)
    def test_high_alert_only(self):
        """Check only has a high alert value"""
        self.metrics_check.warning_value = None
        self.metrics_check.high_alert_value = 9.0
        result = self.metrics_check._run()
        self.assertEqual(result.check, self.metrics_check)
        self.assertFalse(result.succeeded)
        self.assertEqual(result.error, u'prod.good.data: 9.2 <= 9.0')
        self.assertEqual(self.metrics_check.importance, Service.CRITICAL_STATUS)
