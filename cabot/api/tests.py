# -*- coding: utf-8 -*-

from cabot.cabotapp.tests.tests_basic import LocalTestCase
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
import json
import os
import base64
import time
from mock import Mock, patch
from logging import getLogger
logger = getLogger(__name__)

from cabot.cabotapp.models import Service, Instance, StatusCheckResult, UserProfile, StatusCheck
from cabot.cabotapp.views import StatusCheckReportForm
from cabot.plugins.models import StatusCheckPluginModel, AlertPluginModel, StatusCheckPlugin, AlertPlugin
from cabot.cabotapp.tests.dummy_plugin import plugin as dummy_plugin

class TestAPI(LocalTestCase):
    def setUp(self):
        super(TestAPI, self).setUp()

        self.instance = Instance.objects.create(
            name='Hello',
            address='192.168.0.1',
        )

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
                    'status_checks': [1, 2],
                    'alerts': [],
                    'hackpad_id': None,
                    'instances': [],
                    'id': 1,
                    'url': u'',
                    'overall_status': u'PASSING'
                },
            ],
            'instance': [
                {
                    'name': u'Hello',
                    'users_to_notify': [],
                    'alerts_enabled': True,
                    'status_checks': [],
                    'alerts': [],
                    'hackpad_id': None,
                    'address': u'192.168.0.1',
                    'id': 1,
                    'overall_status': u'PASSING'
                },
            ],
            'statuscheck': [
                {
                    'name': u'Port Open Check for Service',
                    'check_plugin': 'port_open_check',
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'id': 1,
                    'calculated_status': u'passing',
                    'port': 123,
                    'address': 'ports.arachnys.com'
                },
                {
                    'name': u'Port Open Check for Service 2',
                    'check_plugin': 'port_open_check',
                    'active': True,
                    'active': True,
                    'importance': u'ERROR',
                    'frequency': 5,
                    'debounce': 0,
                    'id': 2,
                    'calculated_status': u'passing',
                    'port': 456,
                    'address': 'ports.arachnys.com'
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
                    'instances': [],
                    'id': 2,
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
                    'id': 2,
                    'overall_status': u'PASSING',
                },
            ],
        }

    def test_auth_failure(self):
        response = self.client.get(api_reverse('api:statuscheck-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def normalize_dict(self, operand):
        for key, val in operand.items():
            if isinstance(val, list):
                operand[key] = sorted(val)
        return operand

    def test_gets(self):
        for model, items in self.start_data.items():
            response = self.client.get(api_reverse('api:{}-list'.format(model)),
                                       format='json', HTTP_AUTHORIZATION=self.basic_auth)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), len(items))
            for response_item, item in zip(response.data, items):
                self.assertEqual(self.normalize_dict(response_item), item)
            for item in items:
                response = self.client.get(api_reverse('api:{}-detail'.format(model), args=[item['id']]),
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
                create_response = self.client.post(api_reverse('api:{}-list'.format(model)),
                                                   format='json', data=item, HTTP_AUTHORIZATION=self.basic_auth)
                self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
                self.assertTrue('id' in create_response.data)
                item['id'] = create_response.data['id']
                for field in ('hackpad_id', 'username', 'password'): # See comment above
                    if field in create_response.data:
                        item[field] = None
                self.assertEqual(self.normalize_dict(create_response.data), item)
                get_response = self.client.get(api_reverse('api:{}-detail'.format(model), args=[item['id']]),
                                               format='json', HTTP_AUTHORIZATION=self.basic_auth)                            
                self.assertEqual(self.normalize_dict(get_response.data), item)

class TestAPIFiltering(LocalTestCase):
    def setUp(self):
        super(TestAPIFiltering, self).setUp()

        self.instance = Instance.objects.create(
            name='Hello',
            address='192.168.0.1',
        )
        port_open_check_a = StatusCheck.objects.create(
            name='A Check',
            check_plugin = self.port_open_check_model,
            port=80,
            address='example-A.com'
        )
        port_open_check_z = StatusCheck.objects.create(
            name = 'Z Check',
            check_plugin = self.port_open_check_model,
            port = 80,
            address = 'example-Z.com',
            importance = Service.CRITICAL_STATUS,
            debounce = 1,
        )
        self.expected_filter_result = port_open_check_z
        self.instance.status_checks.add(port_open_check_a, port_open_check_z)

        self.expected_sort_names = ['A Check', 'Port Open Check for Service', 'Port Open Check for Service 2', 'Z Check']

        self.basic_auth = 'Basic {}'.format(
            base64.b64encode(
                '{}:{}'.format(self.username, self.password)
                    .encode(HTTP_HEADER_ENCODING)
            ).decode(HTTP_HEADER_ENCODING)
        )

    def test_query(self):
        response = self.client.get(
            '{}?debounce=1&importance=CRITICAL'.format(
                api_reverse('api:statuscheck-list')
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
                api_reverse('api:statuscheck-list')
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
                api_reverse('api:statuscheck-list')
            ),
            format='json',
            HTTP_AUTHORIZATION=self.basic_auth
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['name'] for item in response.data],
            self.expected_sort_names[::-1]
        )

