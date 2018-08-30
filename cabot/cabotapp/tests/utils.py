# -*- coding: utf-8 -*-

import requests
from django.utils import timezone
from django.contrib.auth.models import Permission, User
from django.core import mail
from rest_framework.test import APITestCase
from twilio import rest
from datetime import timedelta
import json
import os
import socket
from celery.task import task
from mock import Mock

from cabot.cabotapp.models import (
    JenkinsStatusCheck,
    HttpStatusCheck,
    TCPStatusCheck,
    Service,
    Schedule,
    StatusCheckResult,
)


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
            Permission.objects.get(codename='add_service'),
            Permission.objects.get(codename='add_httpstatuscheck'),
            Permission.objects.get(codename='add_jenkinsstatuscheck'),
            Permission.objects.get(codename='add_tcpstatuscheck'),
        )
        self.user.save()

        self.jenkins_check = JenkinsStatusCheck.objects.create(
            id=10101,
            name='Jenkins Check',
            created_by=self.user,
            importance=Service.ERROR_STATUS,
            max_queued_build_time=10,
            max_build_failures=5
        )

        self.jenkins_check2 = JenkinsStatusCheck.objects.create(
            id=10104,
            name='Jenkins Check 2',
            created_by=self.user,
            importance=Service.ERROR_STATUS,
            max_queued_build_time=10,
            max_build_failures=0
        )

        self.http_check = HttpStatusCheck.objects.create(
            id=10102,
            name='Http Check',
            created_by=self.user,
            importance=Service.CRITICAL_STATUS,
            endpoint='http://arachnys.com',
            timeout=10,
            status_code='200',
            text_match=None,
        )
        self.tcp_check = TCPStatusCheck.objects.create(
            id=10103,
            name='TCP Check',
            created_by=self.user,
            importance=Service.ERROR_STATUS,
            address='github.com',
            port=80,
            timeout=6,
        )

        # Set ical_url for schedule to filename we're using for mock response
        self.schedule = Schedule.objects.create(
            name='Principal',
            ical_url='calendar_response.ics',
        )
        self.secondary_schedule = Schedule.objects.create(
            name='Secondary',
            ical_url='calendar_response_different.ics',
            fallback_officer=self.user,
        )
        self.schedule.save()
        self.secondary_schedule.save()

        self.service = Service.objects.create(
            id=2194,
            name='Service',
        )
        self.service.save()
        self.service.schedules.add(self.schedule)
        self.service.status_checks.add(
            self.jenkins_check,
            self.http_check,
            self.tcp_check)

        # Failing is second most recent
        self.older_result = StatusCheckResult(
            check=self.http_check,
            time=timezone.now() - timedelta(seconds=60),
            time_complete=timezone.now() - timedelta(seconds=59),
            succeeded=False
        )
        self.older_result.save()
        # Passing is most recent
        self.most_recent_result = StatusCheckResult(
            check=self.http_check,
            time=timezone.now() - timedelta(seconds=1),
            time_complete=timezone.now(),
            succeeded=True
        )
        self.most_recent_result.save()
        self.http_check.save()  # Will recalculate status


def get_content(fname):
    '''Get the contents of the named fixtures file'''
    path = os.path.join(os.path.dirname(__file__), 'fixtures/%s' % fname)
    with open(path) as f:
        return f.read()


def fake_jenkins_success(*args, **kwargs):
    resp = Mock()
    resp.raise_for_status.return_value = resp
    resp.json = lambda: json.loads(get_content('jenkins_success.json'))
    resp.status_code = 200
    return resp


def fake_jenkins_response(*args, **kwargs):
    resp = Mock()
    resp.raise_for_status.return_value = resp
    resp.json = lambda: json.loads(get_content('jenkins_response.json'))
    resp.status_code = 400
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


def fake_tcp_success(*args, **kwargs):
    resp = Mock()
    resp.query.return_value = Mock()
    return resp


def fake_tcp_failure(*args, **kwargs):
    raise socket.timeout


def fake_calendar(*args, **kwargs):
    resp = Mock()
    resp.content = get_content(args)
    resp.status_code = 200
    return resp


@task(ignore_result=True)
def fake_run_status_check(*args, **kwargs):
    resp = Mock()
    return resp


def throws_timeout(*args, **kwargs):
    raise requests.RequestException(u'something bad happened')
