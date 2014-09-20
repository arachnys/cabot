# -*- coding: utf-8 -*-

import requests
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from django.test.client import Client
from django.contrib.auth.models import Permission
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework.test import APITestCase
from rest_framework.reverse import reverse as api_reverse
from cabot.cabotapp.models import (
    GraphiteStatusCheck, JenkinsStatusCheck,
    HttpStatusCheck, ICMPStatusCheck, Service, Instance, StatusCheckResult)
from cabot.cabotapp.views import StatusCheckReportForm
from mock import Mock, patch
from twilio import rest
from django.utils import timezone
from django.core import mail
from datetime import timedelta, date
import json
import os
import base64

def get_content(fname):
    path = os.path.join(os.path.dirname(__file__), 'fixtures/%s' % fname)
    with open(path) as f:
        return f.read()


class LocalTestCase(APITestCase):

    def setUp(self):
        requests.get = Mock()
        requests.post = Mock()
        rest.TwilioRestClient = Mock()
        mail.send_mail = Mock()
        self.create_dummy_data()
        super(LocalTestCase, self).setUp()

    def create_dummy_data(self):
        self.username = 'testuser'
        self.password = 'testuserpassword'
        self.user = User.objects.create(username=self.username)
        self.user.set_password(self.password)
        self.user.user_permissions.add(
            Permission.objects.get(codename='add_instance'),
            Permission.objects.get(codename='add_service'),
            Permission.objects.get(codename='add_httpstatuscheck'),
            Permission.objects.get(codename='add_graphitestatuscheck'),
            Permission.objects.get(codename='add_jenkinsstatuscheck'),
            Permission.objects.get(codename='add_icmpstatuscheck'),
        )
        self.user.save()
        self.graphite_check = GraphiteStatusCheck.objects.create(
            name='Graphite Check',
            metric='stats.fake.value',
            check_type='>',
            value='9.0',
            created_by=self.user,
            importance=Service.ERROR_STATUS,
        )
        self.jenkins_check = JenkinsStatusCheck.objects.create(
            name='Jenkins Check',
            created_by=self.user,
            importance=Service.ERROR_STATUS,
            max_queued_build_time=10,
        )
        self.http_check = HttpStatusCheck.objects.create(
            name='Http Check',
            created_by=self.user,
            importance=Service.CRITICAL_STATUS,
            endpoint='http://arachnys.com',
            timeout=10,
            status_code='200',
            text_match=None,
        )
        self.service = Service.objects.create(
            name='Service',
        )

        self.service.status_checks.add(
            self.graphite_check, self.jenkins_check, self.http_check)
        # failing is second most recent
        self.older_result = StatusCheckResult(
            check=self.graphite_check,
            time=timezone.now() - timedelta(seconds=60),
            time_complete=timezone.now() - timedelta(seconds=59),
            succeeded=False
        )
        self.older_result.save()
        # Passing is most recent
        self.most_recent_result = StatusCheckResult(
            check=self.graphite_check,
            time=timezone.now() - timedelta(seconds=1),
            time_complete=timezone.now(),
            succeeded=True
        )
        self.most_recent_result.save()
        self.graphite_check.save()  # Will recalculate status


def fake_graphite_response(*args, **kwargs):
    resp = Mock()
    resp.json = json.loads(get_content('graphite_response.json'))
    resp.status_code = 200
    return resp


def fake_jenkins_response(*args, **kwargs):
    resp = Mock()
    resp.json = json.loads(get_content('jenkins_response.json'))
    resp.status_code = 200
    return resp


def jenkins_blocked_response(*args, **kwargs):
    resp = Mock()
    resp.json = json.loads(get_content('jenkins_blocked_response.json'))
    resp.status_code = 200
    return resp


def fake_http_200_response(*args, **kwargs):
    resp = Mock()
    resp.content = get_content('http_response.html')
    resp.status_code = 200
    return resp


def fake_http_404_response(*args, **kwargs):
    resp = Mock()
    resp.content = get_content('http_response.html')
    resp.status_code = 404
    return resp


def throws_timeout(*args, **kwargs):
    raise requests.RequestException(u'фиктивная ошибка innit')


class TestCheckRun(LocalTestCase):


    def test_calculate_service_status(self):
        self.assertEqual(self.graphite_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.assertEqual(self.jenkins_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.assertEqual(self.http_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.service.update_status()
        self.assertEqual(self.service.overall_status, Service.PASSING_STATUS)

        # Now two most recent are failing
        self.most_recent_result.succeeded = False
        self.most_recent_result.save()
        self.graphite_check.last_run = timezone.now()
        self.graphite_check.save()
        self.assertEqual(self.graphite_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)
        self.service.update_status()
        self.assertEqual(self.service.overall_status, Service.ERROR_STATUS)

        # Will fail even if second one is working
        self.older_result.succeeded = True
        self.older_result.save()
        self.graphite_check.save()
        self.assertEqual(self.graphite_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)
        self.service.update_status()
        self.assertEqual(self.service.overall_status, Service.ERROR_STATUS)

        # Changing debounce will change it up
        self.graphite_check.debounce = 1
        self.graphite_check.save()
        self.assertEqual(self.graphite_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.service.update_status()
        self.assertEqual(self.service.overall_status, Service.PASSING_STATUS)

    @patch('cabot.cabotapp.graphite.requests.get', fake_graphite_response)
    def test_graphite_run(self):
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 2)
        self.graphite_check.run()
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 3)
        # Most recent check failed
        self.assertFalse(self.graphite_check.last_result().succeeded)
        self.assertEqual(self.graphite_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)
        # This should now pass
        self.graphite_check.value = '11.0'
        self.graphite_check.save()
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 3)
        self.graphite_check.run()
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 4)
        self.assertEqual(self.graphite_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)

    @patch('cabot.cabotapp.jenkins.requests.get', fake_jenkins_response)
    def test_jenkins_run(self):
        checkresults = self.jenkins_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 0)
        self.jenkins_check.run()
        checkresults = self.jenkins_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 1)
        self.assertFalse(self.jenkins_check.last_result().succeeded)

    @patch('cabot.cabotapp.jenkins.requests.get', jenkins_blocked_response)
    def test_jenkins_blocked_build(self):
        checkresults = self.jenkins_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 0)
        self.jenkins_check.run()
        checkresults = self.jenkins_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 1)
        self.assertFalse(self.jenkins_check.last_result().succeeded)

    @patch('cabot.cabotapp.models.requests.get', throws_timeout)
    def test_timeout_handling_in_jenkins(self):
        checkresults = self.jenkins_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 0)
        self.jenkins_check.run()
        checkresults = self.jenkins_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 1)
        self.assertTrue(self.jenkins_check.last_result().succeeded)
        self.assertIn(u'Error fetching from Jenkins - фиктивная ошибка',
                      self.jenkins_check.last_result().error)

    @patch('cabot.cabotapp.models.requests.get', fake_http_200_response)
    def test_http_run(self):
        checkresults = self.http_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 0)
        self.http_check.run()
        checkresults = self.http_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 1)
        self.assertTrue(self.http_check.last_result().succeeded)
        self.assertEqual(self.http_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.http_check.text_match = u'blah blah'
        self.http_check.save()
        self.http_check.run()
        self.assertFalse(self.http_check.last_result().succeeded)
        self.assertEqual(self.http_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)
        # Unicode
        self.http_check.text_match = u'как закалялась сталь'
        self.http_check.save()
        self.http_check.run()
        self.assertFalse(self.http_check.last_result().succeeded)
        self.assertEqual(self.http_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)

    @patch('cabot.cabotapp.models.requests.get', throws_timeout)
    def test_timeout_handling_in_http(self):
        checkresults = self.http_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 0)
        self.http_check.run()
        checkresults = self.http_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 1)
        self.assertFalse(self.http_check.last_result().succeeded)
        self.assertIn(u'Request error occurred: фиктивная ошибка innit',
                      self.http_check.last_result().error)

    @patch('cabot.cabotapp.models.requests.get', fake_http_404_response)
    def test_http_run_bad_resp(self):
        checkresults = self.http_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 0)
        self.http_check.run()
        checkresults = self.http_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 1)
        self.assertFalse(self.http_check.last_result().succeeded)
        self.assertEqual(self.http_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)


class TestInstances(LocalTestCase):

    def test_duplicate_instance(self):
        instances = Instance.objects.all()
        self.assertEqual(len(instances), 0)
        self.instance = Instance.objects.create(
            name='Hello',
            address='192.168.0.1',
        )
        pingcheck = ICMPStatusCheck.objects.create(
            name='Hello check',
        )
        self.instance.status_checks.add(pingcheck)
        self.instance.duplicate()
        instances = Instance.objects.all()
        self.assertEqual(len(instances), 2)
        new = instances.filter(name__icontains='Copy of')[0]
        self.assertEqual(new.name, 'Copy of Hello')
        old = instances.exclude(name__icontains='Copy of')[0]
        self.assertEqual(len(new.status_checks.all()), 1)
        self.assertEqual(len(old.status_checks.all()), 1)
        self.assertNotEqual(new.status_checks.all()[0], old.status_checks.all()[0])


class TestWebInterface(LocalTestCase):

    def setUp(self):
        super(TestWebInterface, self).setUp()
        self.client = Client()

    def test_set_recovery_instructions(self):
        # Get service page - will get 200 from login page
        resp = self.client.get(reverse('update-service', kwargs={'pk':self.service.id}), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('username', resp.content)

        # Log in
        self.client.login(username=self.username, password=self.password)
        resp = self.client.get(reverse('update-service', kwargs={'pk':self.service.id}))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('username', resp.content)

        snippet_link = 'https://sub.hackpad.com/wiki-7YaNlsC11bB.js'
        self.assertEqual(self.service.hackpad_id, None)
        resp = self.client.post(
            reverse('update-service', kwargs={'pk': self.service.id}),
            data={
                'name': self.service.name,
                'hackpad_id': snippet_link,
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        reloaded = Service.objects.get(id=self.service.id)
        self.assertEqual(reloaded.hackpad_id, snippet_link)
        # Now one on the blacklist
        blacklist_link = 'https://unapproved_link.domain.com/wiki-7YaNlsC11bB.js'
        resp = self.client.post(
            reverse('update-service', kwargs={'pk': self.service.id}),
            data={
                'name': self.service.name,
                'hackpad_id': blacklist_link,
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('valid JS snippet link', resp.content)
        reloaded = Service.objects.get(id=self.service.id)
        # Still the same
        self.assertEqual(reloaded.hackpad_id, snippet_link)

    def test_create_instance(self):
        instances = Instance.objects.all()
        self.assertEqual(len(instances), 0)
        self.client.login(username=self.username, password=self.password)
        resp = self.client.post(
            reverse('create-instance'),
            data={
                'name': 'My little instance',
            },
            follow=True,
        )
        instances = Instance.objects.all()
        self.assertEqual(len(instances), 1)
        instance = instances[0]
        self.assertEqual(len(instance.status_checks.all()), 1)

    def test_checks_report(self):
        form = StatusCheckReportForm({
            'service': self.service.id,
            'checks': [self.graphite_check.id],
            'date_from': date.today() - timedelta(days=1),
            'date_to': date.today(),
        })
        self.assertTrue(form.is_valid())
        checks = form.get_report()
        self.assertEqual(len(checks), 1)
        check = checks[0]
        self.assertEqual(len(check.problems), 1)
        self.assertEqual(check.success_rate, 50)


class TestAPI(LocalTestCase):
    def setUp(self):
        super(TestAPI, self).setUp()

        self.instance = Instance.objects.create(
            name='Hello',
            address='192.168.0.1',
        )
        pingcheck = ICMPStatusCheck.objects.create(
            name='Hello check',
        )
        self.instance.status_checks.add(pingcheck)

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
                    'status_checks': [1, 2, 3],
                    'email_alert': False,
                    'hipchat_alert': True,
                    'sms_alert': False,
                    'telephone_alert': False,
                    'hackpad_id': None,
                    'id': 1
                },
            ],
            'instance': [
                {
                    'name': u'Hello',
                    'users_to_notify': [],
                    'alerts_enabled': True,
                    'status_checks': [4],
                    'email_alert': False,
                    'hipchat_alert': True,
                    'sms_alert': False,
                    'telephone_alert': False,
                    'hackpad_id': None,
                    'address': u'192.168.0.1',
                    'id': 1
                },
            ],
            'statuscheck': [
                {
                    'name': u'Graphite Check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'id': 1
                },
                {
                    'name': u'Jenkins Check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'id': 2
                },
                {
                    'name': u'Http Check',
                    'active': True,
                    'importance': u'CRITICAL',
                    'frequency': 5,
                    'debounce': 0,
                    'id': 3
                },
                {
                    'name': u'Hello check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'id': 4
                },
            ],
            'graphitestatuscheck': [
                {
                    'name': u'Graphite Check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'metric': u'stats.fake.value',
                    'check_type': u'>',
                    'value': u'9.0',
                    'expected_num_hosts': 0,
                    'id': 1
                },
            ],
            'httpstatuscheck': [
                {
                    'name': u'Http Check',
                    'active': True,
                    'importance': u'CRITICAL',
                    'frequency': 5,
                    'debounce': 0,
                    'endpoint': u'http://arachnys.com',
                    'username': None,
                    'password': None,
                    'text_match': None,
                    'status_code': u'200',
                    'timeout': 10,
                    'verify_ssl_certificate': True,
                    'id': 3
                },
            ],
            'jenkinsstatuscheck': [
                {
                    'name': u'Jenkins Check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'max_queued_build_time': 10,
                    'id': 2
                },
            ],
            'icmpstatuscheck': [
                {
                    'name': u'Hello check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'id': 4
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
                    'email_alert': False,
                    'hipchat_alert': True,
                    'sms_alert': False,
                    'telephone_alert': False,
                    'hackpad_id': None,
                    'id': 2
                },
            ],
            'instance': [
                {
                    'name': u'posted instance',
                    'users_to_notify': [],
                    'alerts_enabled': True,
                    'status_checks': [],
                    'email_alert': False,
                    'hipchat_alert': True,
                    'sms_alert': False,
                    'telephone_alert': False,
                    'hackpad_id': None,
                    'address': u'255.255.255.255',
                    'id': 2
                },
            ],
            'graphitestatuscheck': [
                {
                    'name': u'posted graphite check',
                    'active': True,
                    'importance': u'CRITICAL',
                    'frequency': 5,
                    'debounce': 0,
                    'metric': u'stats.fakeval2',
                    'check_type': u'<',
                    'value': u'2',
                    'expected_num_hosts': 0,
                    'id': 5
                },
            ],
            'httpstatuscheck': [
                {
                    'name': u'posted http check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'endpoint': u'http://arachnys.com/post_tests',
                    'username': None,
                    'password': None,
                    'text_match': u'text',
                    'status_code': u'201',
                    'timeout': 30,
                    'verify_ssl_certificate': True,
                    'id': 7
                },
            ],
            'jenkinsstatuscheck': [
                {
                    'name': u'posted jenkins check',
                    'active': True,
                    'importance': u'CRITICAL',
                    'frequency': 5,
                    'debounce': 0,
                    'max_queued_build_time': 37,
                    'id': 6
                },
            ],
            'icmpstatuscheck': [
                {
                    'name': u'posted icmp check',
                    'active': True,
                    'importance': u'CRITICAL',
                    'frequency': 5,
                    'debounce': 0,
                    'id': 8
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
                for field in ('hackpad_id', 'username', 'password'): # See comment above
                    if field in create_response.data:
                        item[field] = None
                self.assertEqual(self.normalize_dict(create_response.data), item)
                get_response = self.client.get(api_reverse('{}-detail'.format(model), args=[item['id']]),
                                               format='json', HTTP_AUTHORIZATION=self.basic_auth)
                self.assertEqual(self.normalize_dict(get_response.data), item)

class TestAPIFiltering(LocalTestCase):
    def setUp(self):
        super(TestAPIFiltering, self).setUp()

        self.instance = Instance.objects.create(
            name='Hello',
            address='192.168.0.1',
        )
        pingcheck = ICMPStatusCheck.objects.create(
            name='Hello check',
        )
        self.instance.status_checks.add(pingcheck)

        self.expected_filter_result = JenkinsStatusCheck.objects.create(
            name='Filter test 1',
            debounce=True,
            importance=Service.CRITICAL_STATUS,
        )
        JenkinsStatusCheck.objects.create(
            name='Filter test 2',
            debounce=True,
            importance=Service.WARNING_STATUS,
        )
        JenkinsStatusCheck.objects.create(
            name='Filter test 3',
            debounce=False,
            importance=Service.CRITICAL_STATUS,
        )

        GraphiteStatusCheck.objects.create(
            name='Z check',
            metric='stats.fake.value',
            check_type='>',
            value='9.0',
            created_by=self.user,
            importance=Service.ERROR_STATUS,
        )
        GraphiteStatusCheck.objects.create(
            name='A check',
            metric='stats.fake.value',
            check_type='>',
            value='9.0',
            created_by=self.user,
            importance=Service.ERROR_STATUS,
        )
        self.expected_sort_names = ['A check', 'Graphite Check', 'Z check']

        self.basic_auth = 'Basic {}'.format(
            base64.b64encode(
                '{}:{}'.format(self.username, self.password)
                    .encode(HTTP_HEADER_ENCODING)
            ).decode(HTTP_HEADER_ENCODING)
        )

    def test_query(self):
        response = self.client.get(
            '{}?debounce=1&importance=CRITICAL'.format(
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
                api_reverse('graphitestatuscheck-list')
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
                api_reverse('graphitestatuscheck-list')
            ), 
            format='json', 
            HTTP_AUTHORIZATION=self.basic_auth
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['name'] for item in response.data], 
            self.expected_sort_names[::-1]
        )
