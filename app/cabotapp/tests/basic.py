import requests
from cabotapp.alert import _send_hipchat_alert
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth.models import User
from cabotapp.models import (StatusCheck, GraphiteStatusCheck, JenkinsStatusCheck,
    HttpStatusCheck, Service, StatusCheckResult)
from mock import Mock, patch
from twilio import rest
from django.core import mail
from datetime import timedelta
import json
import os

def get_content(fname):
  path = os.path.join(os.path.dirname(__file__), 'fixtures/%s' % fname)
  with open(path) as f:
    return f.read()

class LocalTestCase(TestCase):
  def setUp(self):
    requests.get = Mock()
    requests.post = Mock()
    rest.TwilioRestClient = Mock()
    mail.send_mail = Mock()
    super(LocalTestCase, self).setUp()

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

class TestCheckRun(LocalTestCase):
  def setUp(self):
    super(TestCheckRun, self).setUp()
    self.user = User.objects.create(username='testuser')
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
    self.service.status_checks.add(self.graphite_check, self.jenkins_check, self.http_check)
    # Passing is most recent
    self.most_recent_result = StatusCheckResult(
      check=self.graphite_check,
      time=timezone.now()-timedelta(seconds=1),
      time_complete=timezone.now(),
      succeeded=True
    )
    self.most_recent_result.save()
    # failing is second most recent
    self.older_result = StatusCheckResult(
      check=self.graphite_check,
      time=timezone.now()-timedelta(seconds=60),
      time_complete=timezone.now()-timedelta(seconds=59),
      succeeded=False
    )
    self.older_result.save()
    self.graphite_check.save() # Will recalculate status

  def test_calculate_service_status(self):
    self.assertEqual(self.graphite_check.calculated_status, Service.CALCULATED_PASSING_STATUS)
    self.assertEqual(self.jenkins_check.calculated_status, Service.CALCULATED_PASSING_STATUS)
    self.assertEqual(self.http_check.calculated_status, Service.CALCULATED_PASSING_STATUS)
    self.service.update_status()
    self.assertEqual(self.service.overall_status, Service.PASSING_STATUS)

    # Now two most recent are failing
    self.most_recent_result.succeeded = False
    self.most_recent_result.save()
    self.graphite_check.save()
    self.assertEqual(self.graphite_check.calculated_status, Service.CALCULATED_FAILING_STATUS)
    self.service.update_status()
    self.assertEqual(self.service.overall_status, Service.ERROR_STATUS)

    # Will fail even if second one is working
    self.older_result.succeeded = True
    self.older_result.save()
    self.graphite_check.save()
    self.assertEqual(self.graphite_check.calculated_status, Service.CALCULATED_FAILING_STATUS)
    self.service.update_status()
    self.assertEqual(self.service.overall_status, Service.ERROR_STATUS)

    # Changing debounce will change it up
    self.graphite_check.debounce = 1
    self.graphite_check.save()
    self.assertEqual(self.graphite_check.calculated_status, Service.CALCULATED_PASSING_STATUS)
    self.service.update_status()
    self.assertEqual(self.service.overall_status, Service.PASSING_STATUS)

  @patch('cabotapp.graphite.requests.get', fake_graphite_response)
  def test_graphite_run(self):
    checkresults = self.graphite_check.statuscheckresult_set.all()
    self.assertEqual(len(checkresults), 2)
    self.graphite_check.run()
    checkresults = self.graphite_check.statuscheckresult_set.all()
    self.assertEqual(len(checkresults), 3)
    # Most recent check failed
    self.assertFalse(self.graphite_check.last_result().succeeded)
    self.assertEqual(self.graphite_check.calculated_status, Service.CALCULATED_FAILING_STATUS)
    # This should now pass
    self.graphite_check.value = '11.0'
    self.graphite_check.save()
    checkresults = self.graphite_check.statuscheckresult_set.all()
    self.assertEqual(len(checkresults), 3)
    self.graphite_check.run()
    checkresults = self.graphite_check.statuscheckresult_set.all()
    self.assertEqual(len(checkresults), 4)
    self.assertEqual(self.graphite_check.calculated_status, Service.CALCULATED_PASSING_STATUS)

  @patch('cabotapp.jenkins.requests.get', fake_jenkins_response)
  def test_jenkins_run(self):
    checkresults = self.jenkins_check.statuscheckresult_set.all()
    self.assertEqual(len(checkresults), 0)
    self.jenkins_check.run()
    checkresults = self.jenkins_check.statuscheckresult_set.all()
    self.assertEqual(len(checkresults), 1)
    self.assertFalse(self.jenkins_check.last_result().succeeded)

  @patch('cabotapp.models.requests.get', fake_http_200_response)
  def test_http_run(self):
    checkresults = self.http_check.statuscheckresult_set.all()
    self.assertEqual(len(checkresults), 0)
    self.http_check.run()
    checkresults = self.http_check.statuscheckresult_set.all()
    self.assertEqual(len(checkresults), 1)
    self.assertTrue(self.http_check.last_result().succeeded)
    self.assertEqual(self.http_check.calculated_status, Service.CALCULATED_PASSING_STATUS)
    self.http_check.text_match = 'blah blah'
    self.http_check.save()
    self.http_check.run()
    self.assertFalse(self.http_check.last_result().succeeded)
    self.assertEqual(self.http_check.calculated_status, Service.CALCULATED_FAILING_STATUS)

  @patch('cabotapp.models.requests.get', fake_http_404_response)
  def test_http_run_bad_resp(self):
    checkresults = self.http_check.statuscheckresult_set.all()
    self.assertEqual(len(checkresults), 0)
    self.http_check.run()
    checkresults = self.http_check.statuscheckresult_set.all()
    self.assertEqual(len(checkresults), 1)
    self.assertFalse(self.http_check.last_result().succeeded)
    self.assertEqual(self.http_check.calculated_status, Service.CALCULATED_FAILING_STATUS)





