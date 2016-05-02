from django.contrib.auth.models import User
from django import forms
from django.core.exceptions import ValidationError
from cabot.cabotapp.tests.tests_basic import LocalTestCase
from cabot.cabotapp.tests.dummy_plugin.plugin import (
        ChatMessengerAlertPlugin, PortOpenStatusCheckPlugin)
from cabot.cabotapp.models import Service, Instance, StatusCheck
from .models import Plugin, AlertPlugin, PluginModel, AlertPluginModel

class TestCabotStatusCheckPlugins(LocalTestCase):
    def setUp(self):
        ret = super(TestCabotStatusCheckPlugins, self).setUp()
        self.status_check = StatusCheck.objects.create(
                check_plugin = self.port_open_check_model,
                name = 'Example SSH open check',
                port = 22,
                address = 'ssh.example.com'
                )
        return ret

    def test_status_check_creation(self):
        self.status_check = StatusCheck.objects.create(
                check_plugin = self.port_open_check_model,
                name = 'Example SSH open check',
                port = 22,
                address = 'ssh.example.com'
                )
        # Refetch from database.
        status_check = StatusCheck.objects.get(pk=self.status_check.pk)
        self.assertEqual(status_check.port, 22)
        self.assertEqual(status_check.address, 'ssh.example.com')

    def test_status_check_update(self):
        self.status_check.port = 100
        self.status_check.address = '100.example.com'
        self.status_check.save()
        # refetch
        status_check = StatusCheck.objects.get(pk=self.status_check.pk)
        self.assertEqual(status_check.port, 100)
        self.assertEqual(status_check.address, '100.example.com')

    def test_status_check_field_validation(self):
        with self.assertRaises(ValidationError):
            status_check = StatusCheck.objects.create(
                    check_plugin = self.port_open_check_model,
                    name = 'Example port check',
                    port = -1, # Illegal!
                    address = 'ports.example.com'
                    )
        with self.assertRaises(ValidationError):
            status_check = StatusCheck.objects.create(
                    check_plugin = self.port_open_check_model,
                    name = 'Example port check',
                    port = 'port 80', # Wrong type
                    address = 'ports.example.com'
                    )
        with self.assertRaises(ValidationError):
            status_check = StatusCheck.objects.create(
                    check_plugin = self.port_open_check_model,
                    name = 'Example port check',
                    address = 'ports.example.com' # Missing required port
                    )
        with self.assertRaises(ValidationError):
            self.status_check.port = 'updated wrong type'
            self.status_check.save()


class TestCabotAlertPlugins(LocalTestCase):

    def test_user_settings(self):
        self.assertEqual(self.user.chat_messenger_alert_settings.nickname,
                                                'Xx__CabotMaster420__xX')
        self.user.chat_messenger_alert_settings.nickname = 'new_nickname'
        self.assertEqual(self.user.chat_messenger_alert_settings.nickname,
                                                'new_nickname')

