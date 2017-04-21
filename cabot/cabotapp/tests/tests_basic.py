# -*- coding: utf-8 -*-

import base64
import json
import time
from datetime import timedelta, date

import os
import requests
from cabot.cabotapp.graphite import parse_metric
from cabot.cabotapp.alert import update_alert_plugins, AlertPlugin
from cabot.cabotapp.models import (
    GraphiteStatusCheck, JenkinsStatusCheck,
    HttpStatusCheck, ICMPStatusCheck, Service, Instance,
    StatusCheckResult, minimize_targets, ServiceStatusSnapshot)
from cabot.cabotapp.calendar import get_events
from cabot.cabotapp.views import StatusCheckReportForm
from cabot.cabotapp import tasks
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test.utils import override_settings
from django.utils import timezone
from freezegun import freeze_time
from mock import Mock, patch
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework.reverse import reverse as api_reverse
from rest_framework.test import APITestCase
from twilio import rest

# Silence noisy celery logs in tests.
import logging
from celery.utils.log import logger as celery_logger
celery_logger.setLevel(logging.WARNING)


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

        self.alert_plugin = AlertPlugin.objects.first()
        self.service.alerts.add(
            self.alert_plugin
        )

        self.service.status_checks.add(
            self.graphite_check, self.jenkins_check, self.http_check)
        # failing is second most recent
        self.older_result = StatusCheckResult(
            status_check=self.graphite_check,
            time=timezone.now() - timedelta(seconds=60),
            time_complete=timezone.now() - timedelta(seconds=59),
            succeeded=False
        )
        self.older_result.save()
        # Passing is most recent
        self.most_recent_result = StatusCheckResult(
            status_check=self.graphite_check,
            time=timezone.now() - timedelta(seconds=1),
            time_complete=timezone.now(),
            succeeded=True
        )
        self.most_recent_result.save()
        self.graphite_check.save()  # Will recalculate status


def fake_graphite_response(*args, **kwargs):
    resp = Mock()
    resp.json = lambda: json.loads(get_content('graphite_response.json'))
    resp.status_code = 200
    return resp


def fake_graphite_series_response(*args, **kwargs):
    resp = Mock()
    resp.json = lambda: json.loads(get_content('graphite_avg_response.json'))
    resp.status_code = 200
    return resp


def fake_empty_graphite_response(*args, **kwargs):
    resp = Mock()
    resp.json = lambda: json.loads(get_content('graphite_null_response.json'))
    resp.status_code = 200
    return resp


def fake_slow_graphite_response(*args, **kwargs):
    resp = Mock()
    time.sleep(0.1)
    resp.json = lambda: json.loads(get_content('graphite_null_response.json'))
    resp.status_code = 200
    return resp


def fake_jenkins_response(*args, **kwargs):
    resp = Mock()
    resp.json = lambda: json.loads(get_content('jenkins_response.json'))
    resp.status_code = 200
    return resp


def jenkins_blocked_response(*args, **kwargs):
    resp = Mock()
    resp.json = lambda: json.loads(get_content('jenkins_blocked_response.json'))
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


def fake_gcal_response(*args, **kwargs):
    resp = Mock()
    resp.content = get_content('gcal_response.ics')
    resp.status_code = 200
    return resp


def fake_recurring_response(*args, **kwargs):
    resp = Mock()
    resp.content = get_content('recurring_response.ics')
    resp.status_code = 200
    return resp


def fake_recurring_response_notz(*args, **kwargs):
    resp = Mock()
    resp.content = get_content('recurring_response_notz.ics')
    resp.status_code = 200
    return resp


def throws_timeout(*args, **kwargs):
    raise requests.RequestException(u'фиктивная ошибка innit')


class TestPolymorphic(LocalTestCase):
    def test_polymorphic(self):
        plugin = AlertPlugin.objects.first()

        self.assertIn(type(plugin), AlertPlugin.__subclasses__())


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

    @patch('cabot.cabotapp.alert.AlertPlugin._send_alert')
    @patch('cabot.cabotapp.alert.AlertPlugin._send_alert_update')
    @freeze_time('2017-03-02 10:30:43.714759')
    def test_alert_acknowledgement(self, fake_send_alert_update, fake_send_alert):
        self.assertEqual(self.service.overall_status, Service.PASSING_STATUS)
        self.most_recent_result.succeeded = False
        self.most_recent_result.save()
        self.graphite_check.last_run = timezone.now()
        self.graphite_check.save()
        self.assertEqual(self.graphite_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)
        self.service.update_status()
        fake_send_alert.assert_called()
        fake_send_alert.reset_mock()

        with freeze_time(timezone.now() + timedelta(minutes=30)):
            self.service.update_status()
            fake_send_alert.assert_called()
            fake_send_alert.reset_mock()

        self.service.acknowledge_alert(user=self.user)
        self.service.update_status()
        self.assertEqual(self.service.unexpired_acknowledgement().user, self.user)
        self.assertFalse(fake_send_alert_update.called)

        with freeze_time(timezone.now() + timedelta(minutes=60)):
            self.service.update_status()
            self.assertEqual(self.service.unexpired_acknowledgement(), None)
            fake_send_alert.assert_called()

        with freeze_time(timezone.now() + timedelta(minutes=90)):
            self.service.acknowledge_alert(user=self.user)
            self.service.update_status()
            self.assertEqual(self.service.unexpired_acknowledgement().user, self.user)
            fake_send_alert_update.assert_called()

    @patch('cabot.cabotapp.graphite.requests.get', fake_graphite_response)
    def test_graphite_run(self):
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 2)
        self.graphite_check.utcnow = 1387818601 # see graphite_response.json for this magic timestamp
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
        # As should this - passing but failures allowed
        self.graphite_check.allowed_num_failures = 2
        self.graphite_check.save()
        self.graphite_check.run()
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 5)
        self.assertEqual(self.graphite_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        # As should this - failing but 1 failure allowed
        # (in test data, one data series is entirely below 9 and one goes above)
        self.graphite_check.value = '9.0'
        self.graphite_check.allowed_num_failures = 1
        self.graphite_check.save()
        self.graphite_check.run()
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 6)
        self.assertEqual(self.graphite_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS,
                         list(checkresults)[-1].error)
        # And it will fail if we don't allow failures
        self.graphite_check.allowed_num_failures = 0
        self.graphite_check.save()
        self.graphite_check.run()
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 7)
        self.assertEqual(self.graphite_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)
        result = checkresults.order_by('-time')[0]
        self.assertEqual(result.error, u'PROD: 9.16092 > 9.0')

    @patch('cabot.cabotapp.graphite.requests.get', fake_graphite_series_response)
    def test_graphite_series_run(self):
        jsn = parse_metric('fake.pattern', utcnow=1387818601)
        self.assertLess(abs(jsn['average_value']-53.26), 0.1)
        self.assertEqual(jsn['series'][0]['max'], 151.0)
        self.assertEqual(jsn['series'][0]['min'], 0.1)

    @patch('cabot.cabotapp.graphite.requests.get', fake_empty_graphite_response)
    def test_graphite_empty_run(self):
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 2)
        self.graphite_check.run()
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 3)
        self.assertTrue(self.graphite_check.last_result().succeeded)
        self.assertEqual(self.graphite_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.graphite_check.expected_num_hosts = 1
        self.graphite_check.save()
        self.graphite_check.run()
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 4)
        self.assertFalse(self.graphite_check.last_result().succeeded)
        self.assertEqual(self.graphite_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)

    @patch('cabot.cabotapp.graphite.requests.get', fake_slow_graphite_response)
    def test_graphite_timing(self):
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 2)
        self.graphite_check.run()
        checkresults = self.graphite_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 3)
        self.assertTrue(self.graphite_check.last_result().succeeded)
        self.assertGreater(list(checkresults)[-1].took, 0.0)

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


class TestDutyRota(LocalTestCase):

    @patch('cabot.cabotapp.models.requests.get', fake_gcal_response)
    def test_duty_rota(self):
        events = get_events()
        self.assertEqual(events[0]['summary'], 'troels')

    @patch('cabot.cabotapp.models.requests.get', fake_recurring_response)
    def test_duty_rota_recurring(self):
        events = get_events()
        events.sort(key=lambda ev: ev['start'])
        curr_summ = events[0]['summary']
        self.assertTrue(curr_summ == 'foo' or curr_summ == 'bar')
        for i in range(0, 60):
            self.assertEqual(events[i]['summary'], curr_summ)
            if(curr_summ == 'foo'):
                curr_summ = 'bar'
            else:
                curr_summ = 'foo'

    @patch('cabot.cabotapp.models.requests.get', fake_recurring_response_notz)
    def test_duty_rota_recurring_notz(self):
        events = get_events()
        events.sort(key=lambda ev: ev['start'])
        curr_summ = events[0]['summary']
        self.assertTrue(curr_summ == 'foo' or curr_summ == 'bar')
        for i in range(0, 60):
            self.assertEqual(events[i]['summary'], curr_summ)
            if(curr_summ == 'foo'):
                curr_summ = 'bar'
            else:
                curr_summ = 'foo'


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

    def test_about_page(self):
        response = self.client.get(reverse('about-cabot'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Version:', response.content)

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
                    'status_checks': [
                        self.graphite_check.id,
                        self.jenkins_check.id,
                        self.http_check.id
                    ],
                    'alerts': [self.alert_plugin.id],
                    'hackpad_id': None,
                    'instances': [],
                    'id': self.service.id,
                    'url': u'',
                    'overall_status': u'PASSING'
                },
            ],
            'instance': [
                {
                    'name': u'Hello',
                    'users_to_notify': [],
                    'alerts_enabled': True,
                    'status_checks': [pingcheck.id],
                    'alerts': [],
                    'hackpad_id': None,
                    'address': u'192.168.0.1',
                    'id': self.instance.id,
                    'overall_status': u'PASSING'
                },
            ],
            'statuscheck': [
                {
                    'name': u'Graphite Check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'id': self.graphite_check.id,
                    'calculated_status': u'passing',
                },
                {
                    'name': u'Jenkins Check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'id': self.jenkins_check.id,
                    'calculated_status': u'passing',
                },
                {
                    'name': u'Http Check',
                    'active': True,
                    'importance': u'CRITICAL',
                    'frequency': 5,
                    'debounce': 0,
                    'id': self.http_check.id,
                    'calculated_status': u'passing',
                },
                {
                    'name': u'Hello check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'id': pingcheck.id,
                    'calculated_status': u'passing',
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
                    'allowed_num_failures': 0,
                    'id': self.graphite_check.id,
                    'calculated_status': u'passing',
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
                    'id': self.http_check.id,
                    'calculated_status': u'passing',
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
                    'id': self.jenkins_check.id,
                    'calculated_status': u'passing',
                },
            ],
            'icmpstatuscheck': [
                {
                    'name': u'Hello check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'id': pingcheck.id,
                    'calculated_status': u'passing',
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
                    'alerts': [self.alert_plugin.id],
                    'hackpad_id': None,
                    'instances': [],
                    'id': self.service.id,
                    'url': u'',
                    'overall_status': u'PASSING',
                },
            ],
            'instance': [
                {
                    'name': u'posted instance',
                    'users_to_notify': [],
                    'alerts_enabled': True,
                    'status_checks': [],
                    'alerts': [],
                    'hackpad_id': None,
                    'address': u'255.255.255.255',
                    'id': self.instance.id,
                    'overall_status': u'PASSING',
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
                    'allowed_num_failures': 0,
                    'id': self.graphite_check.id,
                    'calculated_status': u'passing',
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
                    'id': self.http_check.id,
                    'calculated_status': u'passing',
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
                    'id': self.jenkins_check.id,
                    'calculated_status': u'passing',
                },
            ],
            'icmpstatuscheck': [
                {
                    'name': u'posted icmp check',
                    'active': True,
                    'importance': u'CRITICAL',
                    'frequency': 5,
                    'debounce': 0,
                    'id': pingcheck.id,
                    'calculated_status': u'passing',
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


class TestAlerts(LocalTestCase):
    def setUp(self):
        super(TestAlerts, self).setUp()

        self.warning_http_check = HttpStatusCheck.objects.create(
            name='Http Check',
            created_by=self.user,
            importance=Service.WARNING_STATUS,
            endpoint='http://arachnys.com',
            timeout=10,
            status_code='200',
            text_match=None,
        )
        self.error_http_check = HttpStatusCheck.objects.create(
            name='Http Check',
            created_by=self.user,
            importance=Service.ERROR_STATUS,
            endpoint='http://arachnys.com',
            timeout=10,
            status_code='200',
            text_match=None,
        )
        self.service.status_checks.add(self.warning_http_check, self.error_http_check)
        self.critical_http_check = self.http_check

        self.user.profile.hipchat_alias = "test_user_hipchat_alias"
        self.user.profile.save()

        self.service.users_to_notify.add(self.user)
        self.service.update_status()

    def test_users_to_notify(self):
        self.assertEqual(self.service.users_to_notify.all().count(), 1)
        self.assertEqual(self.service.users_to_notify.get().username, self.user.username)

    @patch('cabot.cabotapp.alert.AlertPlugin._send_alert')
    def test_alert(self, fake_send_alert):
        self.service.alert()
        self.assertEqual(fake_send_alert.call_count, 1)
        fake_send_alert.assert_called()
        self.assertEqual(fake_send_alert.call_args[0][0], self.service)

    def trigger_failing_check(self, check):
        StatusCheckResult(
            status_check=check,
            time=timezone.now() - timedelta(seconds=60),
            time_complete=timezone.now() - timedelta(seconds=59),
            succeeded=False
        ).save()
        check.last_run = timezone.now()
        check.save()

    @patch('cabot.cabotapp.alert.AlertPlugin._send_alert')
    def test_alert_increasing_severity(self, fake_send_alert):
        self.trigger_failing_check(self.warning_http_check)
        self.assertEqual(fake_send_alert.call_count, 1)

        self.trigger_failing_check(self.error_http_check)
        self.assertEqual(fake_send_alert.call_count, 2)

        self.trigger_failing_check(self.critical_http_check)
        self.assertEqual(fake_send_alert.call_count, 3)

    @patch('cabot.cabotapp.alert.AlertPlugin._send_alert')
    def test_alert_decreasing_severity(self, fake_send_alert):
        self.trigger_failing_check(self.critical_http_check)
        self.assertEqual(fake_send_alert.call_count, 1)

        self.trigger_failing_check(self.error_http_check)
        self.assertEqual(fake_send_alert.call_count, 1)

        self.trigger_failing_check(self.warning_http_check)
        self.assertEqual(fake_send_alert.call_count, 1)

    @patch('cabot.cabotapp.alert.AlertPlugin._send_alert')
    def test_alert_alternating_severity(self, fake_send_alert):
        self.trigger_failing_check(self.error_http_check)
        self.assertEqual(fake_send_alert.call_count, 1)

        self.trigger_failing_check(self.warning_http_check)
        self.assertEqual(fake_send_alert.call_count, 1)

        self.trigger_failing_check(self.error_http_check)
        self.assertEqual(fake_send_alert.call_count, 1)

        self.trigger_failing_check(self.critical_http_check)
        self.assertEqual(fake_send_alert.call_count, 2)

    def test_update_profile_success(self):
        url = reverse('update-alert-user-data', kwargs={'pk':self.user.id, 'alerttype': 'General'})
        self.client.login(username=self.username, password=self.password)

        response = self.client.post(url, follow=True, data={
            "first_name": "Test Name"
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('alert-success', response.content)

    def test_update_profile_fail(self):
        url = reverse('update-alert-user-data', kwargs={'pk':self.user.id, 'alerttype': 'General'})
        self.client.login(username=self.username, password=self.password)

        response = self.client.post(url, follow=True, data={
            "first_name": "Test Name" * 20  # Name too long
        })

        self.assertIn('alert-danger', response.content)

class TestCleanUpTask(LocalTestCase):
    def setUp(self):
        super(TestCleanUpTask, self).setUp()

    def test_cleanup_simple(self):
        initial_results = StatusCheckResult.objects.all().count()
        initial_snapshots = ServiceStatusSnapshot.objects.all().count()

        ServiceStatusSnapshot(
            service=self.service,
            num_checks_active=1,
            num_checks_passing=1,
            num_checks_failing=1,
            overall_status=self.service.overall_status,
            time=timezone.now() - timedelta(days=61),
        ).save()

        StatusCheckResult(
            status_check=self.graphite_check,
            time=timezone.now() - timedelta(days=61),
            time_complete=timezone.now() - timedelta(days=61),
            succeeded=False
        ).save()

        self.assertEqual(StatusCheckResult.objects.all().count(), initial_results + 1)
        tasks.clean_db()
        self.assertEqual(StatusCheckResult.objects.all().count(), initial_results)
        self.assertEqual(ServiceStatusSnapshot.objects.all().count(), initial_snapshots)

    def test_cleanup_batch(self):
        initial_results = StatusCheckResult.objects.all().count()

        for i in range(2):
            StatusCheckResult(
                status_check=self.graphite_check,
                time=timezone.now() - timedelta(days=61),
                time_complete=timezone.now() - timedelta(days=61),
                succeeded=False
            ).save()

        self.assertEqual(StatusCheckResult.objects.all().count(), initial_results + 2)
        tasks.clean_db(batch_size=1)
        self.assertEqual(StatusCheckResult.objects.all().count(), initial_results)

    def test_cleanup_single_batch(self):
        with patch('cabot.cabotapp.tasks.clean_db.apply_async'):
            initial_results = StatusCheckResult.objects.all().count()

            for i in range(2):
                StatusCheckResult(
                    status_check=self.graphite_check,
                    time=timezone.now() - timedelta(days=61),
                    time_complete=timezone.now() - timedelta(days=61),
                    succeeded=False
                ).save()

            self.assertEqual(StatusCheckResult.objects.all().count(), initial_results + 2)
            tasks.clean_db(batch_size=1)
            self.assertEqual(StatusCheckResult.objects.all().count(), initial_results + 1)

    @patch('cabot.cabotapp.tasks.clean_db.apply_async')
    def test_infinite_cleanup_loop(self, mocked_apply_async):
        """
        There is a potential for the cleanup task to constantly call itself
        if every time it re-runs there is at least 1 new object to clean up
        (i.e. every 3 seconds for 60 days a new result is recorded). Make sure
        it only re-calls itself if the whole batch is used.
        """
        with self.settings(CELERY_ALWAYS_EAGER=False):
            initial_results = StatusCheckResult.objects.all().count()

            for i in range(2):
                StatusCheckResult(
                    status_check=self.graphite_check,
                    time=timezone.now() - timedelta(days=61),
                    time_complete=timezone.now() - timedelta(days=61),
                    succeeded=False
                ).save()

            tasks.clean_db(batch_size=2)
            # If full batch is cleaned it should queue itself again
            self.assertTrue(mocked_apply_async.called)

            StatusCheckResult(
                status_check=self.graphite_check,
                time=timezone.now() - timedelta(days=61),
                time_complete=timezone.now() - timedelta(days=61),
                succeeded=False
            ).save()

            mocked_apply_async.reset_mock()
            tasks.clean_db(batch_size=2)
            # This time full batch isn't cleaned (only 1 out of 2) - don't call again
            self.assertFalse(mocked_apply_async.called)


class TestMinimizeTargets(LocalTestCase):
    def test_null(self):
        result = minimize_targets([])
        self.assertEqual(result, [])

    def test_all_same(self):
        result = minimize_targets(["a", "a"])
        self.assertEqual(result, ["a", "a"])

    def test_all_different(self):
        result = minimize_targets(["a", "b"])
        self.assertEqual(result, ["a", "b"])

    def test_same_prefix(self):
        result = minimize_targets(["prefix.a", "prefix.b"])
        self.assertEqual(result, ["a", "b"])

        result = minimize_targets(["prefix.second.a", "prefix.second.b"])
        self.assertEqual(result, ["a", "b"])

    def test_same_suffix(self):
        result = minimize_targets(["a.suffix", "b.suffix"])
        self.assertEqual(result, ["a", "b"])

        result = minimize_targets(["a.suffix.suffix", "b.suffix.suffix"])
        self.assertEqual(result, ["a", "b"])

        result = minimize_targets(["a.b.suffix.suffix", "b.c.suffix.suffix"])
        self.assertEqual(result, ["a.b", "b.c"])

    def test_same_prefix_and_suffix(self):
        result = minimize_targets(["prefix.a.suffix", "prefix.b.suffix"])
        self.assertEqual(result, ["a", "b"])

        result = minimize_targets(["prefix.prefix.a.suffix.suffix",
                                   "prefix.prefix.b.suffix.suffix",])
        self.assertEqual(result, ["a", "b"])
