# -*- coding: utf-8 -*-

import unittest
from datetime import timedelta

import jenkins
from cabot.cabotapp import jenkins as cabot_jenkins
from cabot.cabotapp.models import JenkinsConfig
from cabot.cabotapp.models.jenkins_check_plugin import JenkinsStatusCheck
from django.utils import timezone
from freezegun import freeze_time
from mock import create_autospec, patch


class TestGetStatus(unittest.TestCase):

    def setUp(self):
        self.job = {
            u'inQueue': False,
            u'queueItem': None,
            u'lastSuccessfulBuild': {
                u'number': 12,
            },
            u'lastCompletedBuild': {
                u'number': 12,
            },
            u'lastBuild': {
                u'number': 12,
            },
            u'color': 'blue'
        }

        self.build = {
            u'number': 12,
            u'result': u'SUCCESS'

        }

        self.mock_client = create_autospec(jenkins.Jenkins)
        self.mock_client.get_job_info.return_value = self.job
        self.mock_client.get_build_info.return_value = self.build

        self.mock_config = create_autospec(JenkinsConfig)

    @patch("cabot.cabotapp.jenkins._get_jenkins_client")
    def test_job_passing(self, mock_jenkins):
        mock_jenkins.return_value = self.mock_client

        status = cabot_jenkins.get_job_status(self.mock_config, 'foo')

        expected = {
            'active': True,
            'succeeded': True,
            'job_number': 12,
            'blocked_build_time': None,
            'consecutive_failures': 0,
            'status_code': 200
        }
        self.assertEqual(status, expected)

    @patch("cabot.cabotapp.jenkins._get_jenkins_client")
    def test_job_failing(self, mock_jenkins):
        mock_jenkins.return_value = self.mock_client

        self.build[u'result'] = u'FAILURE'
        self.job[u'lastSuccessfulBuild'] = {
            u'number': 11,
            u'result': u'SUCCESS'
        }

        jenkins_check = JenkinsStatusCheck(
            name="foo",
            jenkins_config=JenkinsConfig(
                name="name",
                jenkins_api="a",
                jenkins_user="u",
                jenkins_pass="p"
            )
        )
        result = JenkinsStatusCheck._run(jenkins_check)

        self.assertEqual(result.consecutive_failures, 1)
        self.assertFalse(result.succeeded)

    @freeze_time('2017-03-02 10:30')
    @patch("cabot.cabotapp.jenkins._get_jenkins_client")
    def test_job_queued_last_succeeded(self, mock_jenkins):
        mock_jenkins.return_value = self.mock_client
        self.job[u'lastBuild'] = {u'number': 13}

        self.job[u'inQueue'] = True
        self.job['queueItem'] = {
            'inQueueSince': float(timezone.now().strftime('%s')) * 1000
        }

        with freeze_time(timezone.now() + timedelta(minutes=10)):
            status = cabot_jenkins.get_job_status(self.mock_config, 'foo')

        expected = {
            'active': True,
            'succeeded': True,
            'job_number': 12,
            'queued_job_number': 13,
            'blocked_build_time': 600,
            'consecutive_failures': 0,
            'status_code': 200
        }
        self.assertEqual(status, expected)

    @freeze_time('2017-03-02 10:30')
    @patch("cabot.cabotapp.jenkins._get_jenkins_client")
    def test_job_queued_last_failed(self, mock_jenkins):
        mock_jenkins.return_value = self.mock_client
        self.job[u'lastBuild'] = {u'number': 13}
        self.job[u'inQueue'] = True
        self.job['queueItem'] = {
            'inQueueSince': float(timezone.now().strftime('%s')) * 1000
        }
        self.build[u'result'] = u'FAILURE'

        with freeze_time(timezone.now() + timedelta(minutes=10)):
            status = cabot_jenkins.get_job_status(self.mock_config, 'foo')

        expected = {
            'active': True,
            'succeeded': False,
            'job_number': 12,
            'queued_job_number': 13,
            'blocked_build_time': 600,
            'consecutive_failures': 0,
            'status_code': 200
        }
        self.assertEqual(status, expected)

    @patch("cabot.cabotapp.jenkins._get_jenkins_client")
    def test_job_unknown(self, mock_jenkins):
        self.mock_client.get_job_info.side_effect = jenkins.NotFoundException()
        mock_jenkins.return_value = self.mock_client

        status = cabot_jenkins.get_job_status(self.mock_config, 'unknown-job')

        expected = {
            'active': None,
            'succeeded': None,
            'job_number': None,
            'blocked_build_time': None,
            'status_code': 404
        }
        self.assertEqual(status, expected)

    @patch("cabot.cabotapp.jenkins._get_jenkins_client")
    def test_job_no_build(self, mock_jenkins):
        unbuilt_job = {
            u'inQueue': False,
            u'queueItem': None,
            u'lastSuccessfulBuild': None,
            u'lastCompletedBuild': None,
            u'lastBuild': None,
            u'color': u'notbuilt'
        }
        self.mock_client.get_job_info.return_value = unbuilt_job
        mock_jenkins.return_value = self.mock_client
        with self.assertRaises(Exception):
            cabot_jenkins.get_job_status(self.mock_config, 'job-unbuilt')

    @patch("cabot.cabotapp.jenkins._get_jenkins_client")
    def test_job_no_good_build(self, mock_jenkins):
        self.mock_client.get_job_info.return_value = {
            u'inQueue': False,
            u'queueItem': None,
            u'lastSuccessfulBuild': None,
            u'lastCompletedBuild': {
                u'number': 1,
            },
            u'lastBuild': {
                u'number': 1,
            },
            u'color': u'red'
        }
        self.mock_client.get_build_info.return_value = {
            u'number': 1,
            u'result': u'FAILURE'
        }
        mock_jenkins.return_value = self.mock_client
        status = cabot_jenkins.get_job_status(self.mock_config, 'job-no-good-build')
        expected = {
            'active': True,
            'succeeded': False,
            'job_number': 1,
            'blocked_build_time': None,
            'consecutive_failures': 1,
            'status_code': 200
        }
        self.assertEqual(status, expected)
