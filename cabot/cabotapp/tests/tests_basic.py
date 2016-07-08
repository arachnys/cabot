# -*- coding: utf-8 -*-

import requests
from django.conf import settings
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from django.test.client import Client
from django.contrib.auth.models import Permission
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework.test import APITestCase
from rest_framework.reverse import reverse as api_reverse
from twilio import rest
from django.core import mail
from datetime import timedelta, date, datetime
import os
import time
from mock import Mock, patch
from logging import getLogger
logger = getLogger(__name__)

from cabot.cabotapp.models import Service, Instance, StatusCheckResult, UserProfile, StatusCheck
from cabot.cabotapp.views import StatusCheckReportForm
from cabot.plugins.models import StatusCheckPluginModel, AlertPluginModel, StatusCheckPlugin, AlertPlugin
from .dummy_plugin import plugin as dummy_plugin


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
        )
        self.user.save()
        self.service = Service.objects.create(
            name='Service',
        )

        self.port_open_check_model = StatusCheckPluginModel.objects.create(slug='port_open_check')
        self.chat_messenger_alert_model = AlertPluginModel.objects.create(slug='chat_messenger_alert')
        # Refetch User model with new chat messenger settings.
        self.user = User.objects.get(username='testuser')
        self.user.chat_messenger_alert_settings.nickname = "Xx__CabotMaster420__xX"

        self.port_open_check = StatusCheck.objects.create(
            name = 'Port Open Check for Service',
            check_plugin = StatusCheckPluginModel.objects.get(slug='port_open_check'),
            created_by = self.user,
            importance = Service.ERROR_STATUS,
            port = 123,
            address = 'ports.arachnys.com'
        )
        self.assertEqual(self.port_open_check.get_variable('port'), 123)
        self.assertEqual(StatusCheck.objects.get().port, 123)
        self.assertEqual(StatusCheck.objects.get().address, 'ports.arachnys.com')

        self.port_open_check_2 = StatusCheck.objects.create(
            name = 'Port Open Check for Service 2',
            check_plugin = StatusCheckPluginModel.objects.get(slug='port_open_check'),
            created_by = self.user,
            importance = Service.ERROR_STATUS,
            port = 456,
            address = 'ports.arachnys.com'
        )

        self.service.status_checks.add(self.port_open_check, self.port_open_check_2)
        # failing is second most recent
        self.older_result = StatusCheckResult(
            status_check=self.port_open_check,
            time=timezone.now() - timedelta(seconds=60),
            time_complete=timezone.now() - timedelta(seconds=59),
            succeeded=False
        )
        self.older_result.save()
        # Passing is most recent
        self.most_recent_result = StatusCheckResult(
            status_check=self.port_open_check,
            time=timezone.now() - timedelta(seconds=1),
            time_complete=timezone.now(),
            succeeded=True
        )
        self.most_recent_result.save()
        self.port_open_check.save()  # Will recalculate status


def throws_timeout(*args, **kwargs):
    raise requests.RequestException(u'фиктивная ошибка innit') # Dummy error init


class TestCheckRun(LocalTestCase):

    def test_calculate_service_status(self):
        self.assertEqual(self.port_open_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.assertEqual(self.port_open_check_2.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.service.update_status()
        self.assertEqual(self.service.overall_status, Service.PASSING_STATUS)

        # Now most recent check is failing
        self.most_recent_result.succeeded = False
        self.most_recent_result.save()
        self.port_open_check.last_run = timezone.now()
        self.port_open_check.save()
        self.assertEqual(self.port_open_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)
        self.service.update_status()
        self.assertEqual(self.service.overall_status, Service.ERROR_STATUS)

        # Will fail even if second one is working
        self.older_result.succeeded = True
        self.older_result.save()
        self.port_open_check.save()
        self.assertEqual(self.port_open_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)
        self.service.update_status()
        self.assertEqual(self.service.overall_status, Service.ERROR_STATUS)

        # Changing debounce will change it up
        self.port_open_check.debounce = 1
        self.port_open_check.save()
        self.assertEqual(self.port_open_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.service.update_status()
        self.assertEqual(self.service.overall_status, Service.PASSING_STATUS)

    @patch('cabot.cabotapp.models.Service.alerts')
    def test_alert_acknowledgement(self, fake_alerts):
        alert = Mock(spec=AlertPluginModel)
        fake_alerts.all.return_value = [alert]

        self.assertEqual(self.service.overall_status, Service.PASSING_STATUS)
        self.most_recent_result.succeeded = False
        self.most_recent_result.save()
        self.port_open_check.last_run = timezone.now()
        self.port_open_check.save()
        self.assertEqual(self.port_open_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)
        self.service.update_status()
        self.assertEqual(alert.send_alert.call_count, 1)
        self.assertEqual(alert.send_alert_update.call_count, 0)

        # 30 mins later. The alert is not acknowledged.
        self.service.last_alert_sent = timezone.now() - timedelta(minutes=30)
        self.service.update_status()
        self.assertEqual(alert.send_alert.call_count, 2)
        self.assertEqual(alert.send_alert_update.call_count, 0)

        # The user acknowledges the alert.
        self.service.acknowledge_alert(user=self.user)
        self.service.last_alert_sent = timezone.now() - timedelta(minutes=30)
        self.service.update_status()
        self.assertEqual(self.service.unexpired_acknowledgement().user, self.user)
        self.assertEqual(alert.send_alert.call_count, 2)
        self.assertEqual(alert.send_alert_update.call_count, 1)


class TestInstances(LocalTestCase):

    def test_duplicate_instance(self):
        instances = Instance.objects.all()
        self.assertEqual(len(instances), 0)
        self.instance = Instance.objects.create(
            name='Hello',
            address='192.168.0.1',
        )
        port_check = StatusCheck.objects.create(
            name='Hello check',
            check_plugin = self.port_open_check_model,
            port = 123,
            address = 'arachnys.com'
        )
        self.instance.status_checks.add(port_check)
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

    def test_checks_report(self):
        form = StatusCheckReportForm({
            'service': self.service.id,
            'checks': [self.port_open_check.id],
            'date_from': date.today() - timedelta(days=1),
            'date_to': date.today(),
        })
        self.assertTrue(form.is_valid())
        checks = form.get_report()
        self.assertEqual(len(checks), 1)
        check = checks[0]
        self.assertEqual(len(check.problems), 1)
        self.assertEqual(check.success_rate, 50)

