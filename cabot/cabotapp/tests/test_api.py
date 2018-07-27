from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework.reverse import reverse as api_reverse
import base64
import json
from cabot.cabotapp.models import (
    ActivityCounter,
    StatusCheck,
    JenkinsStatusCheck,
    Service,
    clone_model,
)
from .utils import LocalTestCase


class TestAPI(LocalTestCase):
    def setUp(self):
        super(TestAPI, self).setUp()

        self.basic_auth = 'Basic {}'.format(
            base64.b64encode(
                '{}:{}'.format(self.username, self.password).encode(HTTP_HEADER_ENCODING)
            ).decode(HTTP_HEADER_ENCODING)
        )

        self.start_data = {
            'service': [
                {
                    'name': u'Service',
                    'users_to_notify': [],
                    'alerts_enabled': True,
                    'status_checks': [10101, 10102, 10103],
                    'alerts': [],
                    'hackpad_id': None,
                    'id': 2194,
                    'url': u''
                },
            ],
            'statuscheck': [
                {
                    'name': u'Jenkins Check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'retries': 0,
                    'id': 10101
                },
                {
                    'name': u'Http Check',
                    'active': True,
                    'importance': u'CRITICAL',
                    'frequency': 5,
                    'retries': 0,
                    'id': 10102
                },
                {
                    'name': u'TCP Check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'retries': 0,
                    'id': 10103
                },
            ],
            'jenkinsstatuscheck': [
                {
                    'name': u'Jenkins Check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'retries': 0,
                    'max_queued_build_time': 10,
                    'id': 10101
                },
            ],
            'httpstatuscheck': [
                {
                    'name': u'Http Check',
                    'active': True,
                    'importance': u'CRITICAL',
                    'frequency': 5,
                    'retries': 0,
                    'endpoint': u'http://arachnys.com',
                    'username': None,
                    'password': None,
                    'text_match': None,
                    'status_code': u'200',
                    'timeout': 10,
                    'verify_ssl_certificate': True,
                    'id': 10102
                },
            ],
            'tcpstatuscheck': [
                {
                    'name': u'TCP Check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'retries': 0,
                    'address': 'github.com',
                    'port': 80,
                    'timeout': 6,
                    'id': 10103
                },
            ],
        }
        self.post_data = {
            'service': [
                {
                    'name': u'posted service',
                    'users_to_notify': [],
                    'alerts_enabled': True,
                    'status_checks': [],
                    'alerts': [],
                    'hackpad_id': None,
                    'id': 2194,
                    'url': u'',
                },
            ],
            'jenkinsstatuscheck': [
                {
                    'name': u'posted jenkins check',
                    'active': True,
                    'importance': u'CRITICAL',
                    'frequency': 5,
                    'retries': 0,
                    'max_queued_build_time': 37,
                    'id': 10101
                },
            ],
            'httpstatuscheck': [
                {
                    'name': u'posted http check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'retries': 0,
                    'endpoint': u'http://arachnys.com/post_tests',
                    'username': None,
                    'password': None,
                    'text_match': u'text',
                    'status_code': u'201',
                    'timeout': 30,
                    'verify_ssl_certificate': True,
                    'id': 10102
                },
            ],
            'tcpstatuscheck': [
                {
                    'name': u'posted tcp check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'retries': 0,
                    'address': 'github.com',
                    'port': 80,
                    'timeout': 6,
                    'id': 10103
                },
            ],
        }

    def test_auth_failure(self):
        response = self.client.get(api_reverse('statuscheck-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def normalize_dict(self, operand):
        for key, val in operand.items():
            if isinstance(val, list):
                operand[key] = sorted(val)
        return operand

    def test_gets(self):
        for model, items in self.start_data.items():
            response = self.client.get(api_reverse('{}-list'.format(model)),
                                       format='json', HTTP_AUTHORIZATION=self.basic_auth)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), len(items))
            for response_item, item in zip(response.data, items):
                self.assertEqual(self.normalize_dict(response_item), item)
            for item in items:
                response = self.client.get(api_reverse('{}-detail'.format(model), args=[item['id']]),
                                           format='json', HTTP_AUTHORIZATION=self.basic_auth)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(self.normalize_dict(response.data), item)

    def test_posts(self):
        for model, items in self.post_data.items():
            for item in items:
                # hackpad_id and other null text fields omitted on create
                # for now due to rest_framework bug:
                # https://github.com/tomchristie/django-rest-framework/issues/1879
                # Update: This has been fixed in master:
                # https://github.com/tomchristie/django-rest-framework/pull/1834
                for field in ('hackpad_id', 'username', 'password'):
                    if field in item:
                        del item[field]
                create_response = self.client.post(api_reverse('{}-list'.format(model)),
                                                   format='json', data=item, HTTP_AUTHORIZATION=self.basic_auth)
                self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
                self.assertTrue('id' in create_response.data)
                item['id'] = create_response.data['id']
                for field in ('hackpad_id', 'username', 'password'):  # See comment above
                    if field in create_response.data:
                        item[field] = None
                self.assertEqual(self.normalize_dict(create_response.data), item)
                get_response = self.client.get(api_reverse('{}-detail'.format(model), args=[item['id']]),
                                               format='json', HTTP_AUTHORIZATION=self.basic_auth)
                self.assertEqual(self.normalize_dict(get_response.data), item)


class TestAPIFiltering(LocalTestCase):
    def setUp(self):
        super(TestAPIFiltering, self).setUp()

        self.expected_filter_result = JenkinsStatusCheck.objects.create(
            name='Filter test 1',
            retries=True,
            importance=Service.CRITICAL_STATUS,
        )
        JenkinsStatusCheck.objects.create(
            name='Filter test 2',
            retries=True,
            importance=Service.WARNING_STATUS,
        )
        JenkinsStatusCheck.objects.create(
            name='Filter test 3',
            retries=False,
            importance=Service.CRITICAL_STATUS,
        )

        self.expected_sort_names = [u'Filter test 1', u'Filter test 2', u'Filter test 3', u'Jenkins Check']

        self.basic_auth = 'Basic {}'.format(
            base64.b64encode(
                '{}:{}'.format(self.username, self.password)
                       .encode(HTTP_HEADER_ENCODING)
            ).decode(HTTP_HEADER_ENCODING)
        )

    def test_query(self):
        response = self.client.get(
            '{}?retries=1&importance=CRITICAL'.format(
                api_reverse('jenkinsstatuscheck-list')
            ),
            format='json',
            HTTP_AUTHORIZATION=self.basic_auth
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]['id'],
            self.expected_filter_result.id
        )

    def test_positive_sort(self):
        response = self.client.get(
            '{}?ordering=name'.format(
                api_reverse('jenkinsstatuscheck-list')
            ),
            format='json',
            HTTP_AUTHORIZATION=self.basic_auth
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['name'] for item in response.data],
            self.expected_sort_names
        )

    def test_negative_sort(self):
        response = self.client.get(
            '{}?ordering=-name'.format(
                api_reverse('jenkinsstatuscheck-list')
            ),
            format='json',
            HTTP_AUTHORIZATION=self.basic_auth
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['name'] for item in response.data],
            self.expected_sort_names[::-1]
        )


class TestActivityCounterAPI(LocalTestCase):
    def _set_activity_counter(self, enabled, count):
        '''Utility function to set the activity counter for the http check'''
        self.http_check.use_activity_counter = enabled
        self.http_check.save()
        ActivityCounter.objects.create(status_check=self.http_check, count=count)

    def test_counter_get(self):
        self._set_activity_counter(True, 1)
        url = '/api/status-checks/activity-counter?'
        expected_body = {
            'check.id': 10102,
            'check.name': 'Http Check',
            'counter.count': 1,
            'counter.enabled': True,
        }
        # Get by id
        response = self.client.get(url + 'id=10102')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), expected_body)
        # Get by name
        response = self.client.get(url + 'name=Http Check')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), expected_body)

    def test_counter_get_error_on_duplicate_names(self):
        self._set_activity_counter(True, 1)
        # If two checks have the same name, check that we error out.
        # This should not be an issue once we enforce uniqueness on the name.
        clone_model(self.http_check)
        self.assertEqual(len(StatusCheck.objects.filter(name='Http Check')), 2)
        url = '/api/status-checks/activity-counter?name=Http Check'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_counter_incr(self):
        self._set_activity_counter(True, 1)
        url = '/api/status-checks/activity-counter?id=10102&action=incr'
        expected_body = {
            'check.id': 10102,
            'check.name': 'Http Check',
            'counter.count': 2,
            'counter.enabled': True,
            'detail': 'counter incremented to 2',
        }
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), expected_body)
        self.assertEqual(StatusCheck.objects.filter(id=10102)[0].activity_counter.count, 2)

    def test_counter_decr(self):
        self._set_activity_counter(True, 1)
        url = '/api/status-checks/activity-counter?id=10102&action=decr'
        expected_body = {
            'check.id': 10102,
            'check.name': 'Http Check',
            'counter.count': 0,
            'counter.enabled': True,
            'detail': 'counter decremented to 0',
        }
        # Decrement counter from one to zero
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), expected_body)
        self.assertEqual(StatusCheck.objects.filter(id=10102)[0].activity_counter.count, 0)
        # Decrementing when counter is zero has no effect
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), expected_body)

    def test_counter_reset(self):
        self._set_activity_counter(True, 11)
        url = '/api/status-checks/activity-counter?id=10102&action=reset'
        expected_body = {
            'check.id': 10102,
            'check.name': 'Http Check',
            'counter.count': 0,
            'counter.enabled': True,
            'detail': 'counter reset to 0',
        }
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), expected_body)
        self.assertEqual(StatusCheck.objects.filter(id=10102)[0].activity_counter.count, 0)

    def test_check_should_run_when_activity_counter_disabled(self):
        self._set_activity_counter(False, 0)
        self.assertTrue(self.http_check.should_run())

    def test_check_should_run_when_activity_counter_positive(self):
        self._set_activity_counter(True, 1)
        self.assertTrue(self.http_check.should_run())

    def test_check_should_not_run_when_activity_counter_zero(self):
        self._set_activity_counter(True, 0)
        self.assertFalse(self.http_check.should_run())

    def test_check_should_not_run_when_activity_counter_missing(self):
        # Set use_activity_counter=True, but do NOT create the actual activity
        # counter DB entry. This used to cause a run_all_checks() to throw a
        # DoesNotExist exception.
        self.http_check.use_activity_counter = True
        self.http_check.save()
        self.assertFalse(self.http_check.should_run())
