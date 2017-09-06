# -*- coding: utf-8 -*-

import unittest
from freezegun import freeze_time
from mock import patch, create_autospec
from cabot.cabotapp import jenkins
from cabot.cabotapp.models import JenkinsConfig
from django.utils import timezone
from datetime import timedelta
import jenkinsapi
from jenkinsapi.custom_exceptions import UnknownJob

class TestGetStatus(unittest.TestCase):

    def setUp(self):
        self.mock_build = create_autospec(jenkinsapi.build.Build)
        self.mock_build.get_number.return_value = 12

        self.mock_job = create_autospec(jenkinsapi.job.Job)
        self.mock_job.is_enabled.return_value = True
        self.mock_job.get_last_completed_build.return_value = self.mock_build

        self.mock_client = create_autospec(jenkinsapi.jenkins.Jenkins)
        self.mock_client.get_job.return_value = self.mock_job

        self.mock_config = create_autospec(JenkinsConfig)

    @patch("cabot.cabotapp.jenkins._get_jenkins_client")
    def test_job_passing(self, mock_jenkins):
        mock_jenkins.return_value = self.mock_client

        self.mock_build.is_good.return_value = True
        self.mock_job.is_queued.return_value = False

        status = jenkins.get_job_status(self.mock_config, 'foo')

        expected = {
            'active': True,
            'succeeded': True,
            'job_number': 12,
            'blocked_build_time': None,
            'status_code': 200
        }
        self.assertEqual(status, expected)

    @patch("cabot.cabotapp.jenkins._get_jenkins_client")
    def test_job_failing(self, mock_jenkins):
        mock_jenkins.return_value = self.mock_client

        self.mock_build.is_good.return_value = False
        self.mock_job.is_queued.return_value = False

        status = jenkins.get_job_status(self.mock_config, 'foo')

        expected = {
            'active': True,
            'succeeded': False,
            'job_number': 12,
            'blocked_build_time': None,
            'status_code': 200
        }
        self.assertEqual(status, expected)

    @freeze_time('2017-03-02 10:30')
    @patch("cabot.cabotapp.jenkins._get_jenkins_client")
    def test_job_queued_last_succeeded(self, mock_jenkins):
        mock_jenkins.return_value = self.mock_client

        self.mock_build.is_good.return_value = True
        self.mock_job.is_queued.return_value = True
        self.mock_job._data = {
            'queueItem': {
                'inQueueSince': float(timezone.now().strftime('%s')) * 1000
            }
        }

        with freeze_time(timezone.now() + timedelta(minutes=10)):
            status = jenkins.get_job_status(self.mock_config, 'foo')

        expected = {
            'active': True,
            'succeeded': True,
            'job_number': 12,
            'blocked_build_time': 600,
            'status_code': 200
        }
        self.assertEqual(status, expected)

    @freeze_time('2017-03-02 10:30')
    @patch("cabot.cabotapp.jenkins._get_jenkins_client")
    def test_job_queued_last_failed(self, mock_jenkins):
        mock_jenkins.return_value = self.mock_client

        self.mock_build.is_good.return_value = False
        self.mock_job.is_queued.return_value = True
        self.mock_job._data = {
            'queueItem': {
                'inQueueSince': float(timezone.now().strftime('%s')) * 1000
            }
        }

        with freeze_time(timezone.now() + timedelta(minutes=10)):
            status = jenkins.get_job_status(self.mock_config, 'foo')

        expected = {
            'active': True,
            'succeeded': False,
            'job_number': 12,
            'blocked_build_time': 600,
            'status_code': 200
        }
        self.assertEqual(status, expected)

    @patch("cabot.cabotapp.jenkins._get_jenkins_client")
    def test_job_unknown(self, mock_jenkins):
        self.mock_client.get_job.side_effect = UnknownJob()
        mock_jenkins.return_value = self.mock_client

        status = jenkins.get_job_status(self.mock_config, 'unknown-job')

        expected = {
            'active': None,
            'succeeded': None,
            'job_number': None,
            'blocked_build_time': None,
            'status_code': 404
        }
        self.assertEqual(status, expected)
