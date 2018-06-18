# -*- coding: utf-8 -*-

from datetime import timedelta
from django.utils import timezone
from cabot.cabotapp import tasks
from mock import patch
from cabot.cabotapp.models import HttpStatusCheck, Service, clone_model
from .utils import (
    LocalTestCase,
    fake_jenkins_success,
    fake_jenkins_response,
    jenkins_blocked_response,
    fake_http_200_response,
    fake_http_404_response,
    fake_tcp_success,
    fake_tcp_failure,
    fake_run_status_check,
    throws_timeout,
)


class TestCheckRun(LocalTestCase):

    def test_calculate_service_status(self):
        self.assertEqual(self.jenkins_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.assertEqual(self.http_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.assertEqual(self.tcp_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.service.update_status()
        self.assertEqual(self.service.overall_status, Service.PASSING_STATUS)

        # Now two most recent are failing
        self.most_recent_result.succeeded = False
        self.most_recent_result.save()
        self.http_check.last_run = timezone.now()
        self.http_check.save()
        self.assertEqual(self.http_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)
        self.service.update_status()
        self.assertEqual(self.service.overall_status, Service.CRITICAL_STATUS)

        # Will fail even if second one is working
        self.older_result.succeeded = True
        self.older_result.save()
        self.http_check.save()
        self.assertEqual(self.http_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)
        self.service.update_status()
        self.assertEqual(self.service.overall_status, Service.CRITICAL_STATUS)

        # Changing the number of retries will change it up
        self.http_check.retries = 1
        self.http_check.save()
        self.assertEqual(self.http_check.calculated_status,
                         Service.CALCULATED_PASSING_STATUS)
        self.service.update_status()
        self.assertEqual(self.service.overall_status, Service.PASSING_STATUS)

    @patch('cabot.cabotapp.jenkins.requests.get', fake_jenkins_success)
    def test_jenkins_success(self):
        checkresults = self.jenkins_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 0)
        self.jenkins_check.run()
        checkresults = self.jenkins_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 1)
        self.assertTrue(self.jenkins_check.last_result().succeeded)

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
        self.assertFalse(self.jenkins_check.last_result().succeeded)
        self.assertIn(u'Error fetching from Jenkins - something bad happened',
                      self.jenkins_check.last_result().error)

    @patch('cabot.cabotapp.models.requests.request', fake_http_200_response)
    def test_http_run(self):
        checkresults = self.http_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 2)
        self.http_check.run()
        checkresults = self.http_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 3)
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
        self.http_check.text_match = u'This is not in the http response!!'
        self.http_check.save()
        self.http_check.run()
        self.assertFalse(self.http_check.last_result().succeeded)
        self.assertEqual(self.http_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)

    @patch('cabot.cabotapp.models.requests.request', throws_timeout)
    def test_timeout_handling_in_http(self):
        checkresults = self.http_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 2)
        self.http_check.run()
        checkresults = self.http_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 3)
        self.assertFalse(self.http_check.last_result().succeeded)
        self.assertIn(u'Request error occurred: something bad happened',
                      self.http_check.last_result().error)

    @patch('cabot.cabotapp.models.requests.request', fake_http_404_response)
    def test_http_run_bad_resp(self):
        checkresults = self.http_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 2)
        self.http_check.run()
        checkresults = self.http_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 3)
        self.assertFalse(self.http_check.last_result().succeeded)
        self.assertEqual(self.http_check.calculated_status,
                         Service.CALCULATED_FAILING_STATUS)

    @patch('cabot.cabotapp.models.socket.create_connection', fake_tcp_success)
    def test_tcp_success(self):
        checkresults = self.tcp_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 0)
        self.tcp_check.run()
        checkresults = self.tcp_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 1)
        self.assertTrue(self.tcp_check.last_result().succeeded)

    @patch('cabot.cabotapp.models.socket.create_connection', fake_tcp_failure)
    def test_tcp_failure(self):
        checkresults = self.tcp_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 0)
        self.tcp_check.run()
        checkresults = self.tcp_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 1)
        self.assertFalse(self.tcp_check.last_result().succeeded)
        self.assertFalse(self.tcp_check.last_result().error, 'timed out')


class TestStatusCheck(LocalTestCase):

    def test_duplicate_statuscheck(self):
        """
        Test that duplicating a statuscheck works and creates a check
        with the name we expect.
        """
        http_checks = HttpStatusCheck.objects.filter(polymorphic_ctype__model='httpstatuscheck')
        self.assertEqual(len(http_checks), 1)

        self.http_check.duplicate()

        http_checks = HttpStatusCheck.objects.filter(polymorphic_ctype__model='httpstatuscheck')
        self.assertEqual(len(http_checks), 2)

        new = http_checks.filter(name__icontains='Copy of')[0]
        old = http_checks.exclude(name__icontains='Copy of')[0]

        # New check should be the same as the old check except for the name
        self.assertEqual(new.name, 'Copy of {}'.format(old.name))
        self.assertEqual(new.endpoint, old.endpoint)
        self.assertEqual(new.status_code, old.status_code)

    @patch('cabot.cabotapp.tasks.run_status_check', fake_run_status_check)
    def test_run_all(self):
        tasks.run_all_checks()
        # TODO: what does this even do?

    def test_check_should_run_if_never_run_before(self):
        self.assertEqual(self.http_check.last_run, None)
        self.assertTrue(self.http_check.should_run())

    def test_check_should_run_based_on_frequency(self):
        freq_mins = 5

        # The check should run if not run within the frequency
        self.http_check.frequency = freq_mins
        self.http_check.last_run = timezone.now() - timedelta(minutes=freq_mins+1)
        self.http_check.save()
        self.assertTrue(self.http_check.should_run())

        # The check should NOT run if run within the frequency
        self.http_check.last_run = timezone.now() - timedelta(minutes=freq_mins-1)
        self.http_check.save()
        self.assertFalse(self.http_check.should_run())

    def test_status_check_name_unique(self):
        # TODO(evan): remove after making name unique
        clone_model(self.http_check)
        models = HttpStatusCheck.objects.filter(name=self.http_check.name)
        self.assertEqual(len(models), 2)
