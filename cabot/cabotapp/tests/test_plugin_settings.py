# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.shortcuts import resolve_url
from django.test import TestCase

from mock import patch

from cabot.cabotapp.alert import AlertPlugin
from cabot.cabotapp.models import Service


class PluginSettingsTest(TestCase):
    def setUp(self):
        self.username = 'testuser'
        self.password = 'testuserpassword'
        self.user = User.objects.create(username=self.username)
        self.user.set_password(self.password)
        self.user.save()
        self.client.login(username=self.username, password=self.password)

    def test_global_settings(self):
        resp = self.client.get(resolve_url('plugin-settings-global'), follow=True)
        self.assertEqual(resp.status_code, 200)

    def test_plugin_settings(self):
        plugin = AlertPlugin.objects.first()

        resp = self.client.get(resolve_url('plugin-settings', plugin_name=plugin.title), follow=True)
        self.assertEqual(resp.status_code, 200)

    def test_plugin_disable(self):
        plugin = AlertPlugin.objects.first()

        resp = self.client.post(resolve_url('plugin-settings', plugin_name=plugin.title), {'enabled': False}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Updated Successfully', resp.content)

    @patch('cabot.cabotapp.alert.AlertPlugin._send_alert')
    def test_plugin_alert_test(self, fake_send_alert):
        plugin = AlertPlugin.objects.first()

        resp = self.client.post(resolve_url('alert-test-plugin'), {'alert_plugin': plugin.id, 'old_status': 'PASSING', 'new_status': 'ERROR'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('ok', resp.content)
        fake_send_alert.assert_called()

    @patch('cabot.cabotapp.alert.AlertPlugin._send_alert')
    def test_global_alert_test(self, fake_send_alert):
        service = Service.objects.create(
            name='Service',
        )

        plugin = AlertPlugin.objects.first()
        service.alerts.add(
            plugin
        )

        resp = self.client.post(resolve_url('alert-test'), {'service': service.id, 'old_status': 'PASSING', 'new_status': 'ERROR'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('ok', resp.content)
        fake_send_alert.assert_called()
