from datetime import timedelta
from mock import ANY, call, patch
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from cabot.cabotapp.alert import send_alert, AlertPlugin
from cabot.cabotapp.models import Schedule, Service, UserProfile
from cabot.cabotapp.tests.tests_basic import LocalTestCase


class TestAlerts(LocalTestCase):
    def setUp(self):
        super(TestAlerts, self).setUp()

        self.user_profile = UserProfile.objects.create(
            user=self.user,
            hipchat_alias="test_user_hipchat_alias",)
        self.user_profile.save()

        self.service.users_to_notify.add(self.user)
        self.service.update_status()

    def test_users_to_notify(self):
        self.assertEqual(self.service.users_to_notify.all().count(), 1)
        self.assertEqual(self.service.users_to_notify.get().username, self.user.username)

    @patch('cabot.cabotapp.models.send_alert')
    def test_alert(self, fake_send_alert):
        self.service.alert()
        self.assertEqual(fake_send_alert.call_count, 1)
        fake_send_alert.assert_called_with(self.service, duty_officers=[], fallback_officers=[])

    @patch('cabot.cabotapp.models.send_alert')
    def test_alert_no_schedule(self, fake_send_alert):
        """Users only should be alerted if there's no oncall schedule"""
        self.service.schedules = []
        self.service.alert()
        self.assertEqual(fake_send_alert.call_count, 1)
        fake_send_alert.assert_called_with(self.service)

    @patch('cabot.cabotapp.models.send_alert')
    def test_alert_empty_schedule(self, fake_send_alert):
        """Test service.alert() when there are no UserProfiles for the oncall schedule.
           The fallback officer shouldb be alerted."""
        service = Service.objects.create(
            name='Test2',
        )
        service.save()
        service.schedules.add(self.secondary_schedule)
        service.update_status()

        service.alert()
        self.assertEqual(fake_send_alert.call_count, 1)
        # Since there are no duty officers with profiles, the fallback will be alerted
        fake_send_alert.assert_called_with(service, duty_officers=[self.user], fallback_officers=[self.user])

    @patch('cabot.cabotapp.models.send_alert')
    def test_alert_multiple_schedules(self, fake_send_alert):
        """
        Make sure service.alert() works with multiple schedules per service.
        """
        user = User.objects.create(username='scheduletest')
        user.save()
        schedule = Schedule.objects.create(
            name='Test',
            ical_url='calendar_response_different.ics',
            fallback_officer=user
        )
        schedule.save()

        service = Service.objects.create(
            name='Test3'
        )
        service.save()
        service.schedules.add(self.secondary_schedule)
        service.schedules.add(schedule)
        service.update_status()

        service.alert()
        self.assertEqual(fake_send_alert.call_count, 2)
        # Since there are no duty officers with profiles, the fallback will be alerted
        calls = [call(service, duty_officers=[self.user], fallback_officers=[self.user]),
                 call(service, duty_officers=[user], fallback_officers=[user])]
        fake_send_alert.has_calls(calls)

    @patch('cabot.cabotapp.alert.AlertPlugin.send_alert')
    def test_alert_plugin(self, fake_send_alert):
        """Test send_alert() when the alert to the duty officer succeeds"""
        alert_plugin = AlertPlugin()
        alert_plugin.save()
        self.service.alerts.add(alert_plugin)

        # No errors in send_alert
        duty_officers = []
        fallback_officers = [UserProfile.objects.all()]
        send_alert(self.service, duty_officers=duty_officers,
                   fallback_officers=fallback_officers)

        # send_alert should be called once with duty_officers
        self.assertEqual(fake_send_alert.call_count, 1)
        fake_send_alert.assert_called_once_with(self.service, ANY, duty_officers)

    @patch('cabot.cabotapp.alert.AlertPlugin.send_alert')
    def test_alert_plugin_fallback(self, fake_send_alert):
        """Test that the fallback officer is alerted if the the alert to the
           duty officer fails"""
        alert_plugin = AlertPlugin()
        alert_plugin.save()

        self.service.alerts.add(alert_plugin)

        # Raise RuntimeError so fallback officer will be alerted
        fake_send_alert.side_effect = RuntimeError

        duty_officers = []
        fallback_officers = [UserProfile.objects.all()]
        send_alert(self.service, duty_officers=duty_officers,
                   fallback_officers=fallback_officers)

        # send_alert should be called with duty_officers and then fallback_officers
        self.assertEqual(fake_send_alert.call_count, 2)
        calls = [call(self.service, ANY, duty_officers),
                 call(self.service, ANY, fallback_officers)]
        fake_send_alert.has_calls(calls)

    @patch('cabot.cabotapp.alert.AlertPlugin.send_alert')
    def test_alert_plugin_no_fallback(self, fake_send_alert):
        """Test an alertplugin failure with no fallback officer"""
        alert_plugin = AlertPlugin()
        alert_plugin.save()

        self.service.alerts.add(alert_plugin)

        # Raise RuntimeError to simulate alerting the duty officer failing
        fake_send_alert.side_effect = RuntimeError

        duty_officers = [UserProfile.objects.all()]
        fallback_officers = []
        send_alert(self.service, duty_officers=duty_officers,
                   fallback_officers=fallback_officers)

        # send_alert should only be called once since there are no fallback officers
        self.assertEqual(fake_send_alert.call_count, 1)
        fake_send_alert.assert_called_once_with(self.service, ANY, duty_officers)


class TestAlertCases(LocalTestCase):
    @patch('cabot.cabotapp.models.send_alert')
    def test_passing_to_critical(self, fake_alert):
        self.service.update_status()
        self.service.overall_status = Service.PASSING_STATUS
        self.service.old_overall_status = Service.CRITICAL_STATUS
        self.service.save()

        self.service.alert()
        self.assertTrue(fake_alert.called)

    @patch('cabot.cabotapp.models.send_alert')
    def test_error_to_passing(self, fake_alert):
        self.service.update_status()
        self.service.overall_status = Service.PASSING_STATUS
        self.service.old_overall_status = Service.ERROR_STATUS
        self.service.save()
        self.service.alert()
        self.assertTrue(fake_alert.called)

    @patch('cabot.cabotapp.models.send_alert')
    def test_critical_to_warning(self, fake_alert):
        """Changing status should alert no matter what"""
        self.service.update_status()
        self.service.overall_status = Service.WARNING_STATUS
        self.service.old_overall_status = Service.CRITICAL_STATUS
        # Make sure we're inside NOTIFICATION_INTERVAL (warning -> warning wouldn't alert)
        self.service.last_alert_sent = timezone.now()
        self.service.save()
        self.service.alert()
        self.assertTrue(fake_alert.called)

    @patch('cabot.cabotapp.models.send_alert')
    def test_warning_to_error(self, fake_alert):
        """Changing status should alert no matter what"""
        self.service.update_status()
        self.service.overall_status = Service.ERROR_STATUS
        self.service.old_overall_status = Service.WARNING_STATUS
        # Make sure we're in ALERT_INTERVAL (error -> error wouldn't alert)
        self.service.last_alert_sent = timezone.now()
        self.service.save()
        self.service.alert()
        self.assertTrue(fake_alert.called)

    @patch('cabot.cabotapp.models.send_alert')
    def test_error_to_error_outside_interval(self, fake_alert):
        """If ALERT_INTERVAL has passed, error -> error should alert"""
        self.service.update_status()
        self.service.overall_status = Service.ERROR_STATUS
        self.service.old_overall_status = Service.ERROR_STATUS
        self.service.last_alert_sent = timezone.now() - 2 * timedelta(minutes=settings.ALERT_INTERVAL)
        self.service.save()
        self.service.alert()
        self.assertTrue(fake_alert.called)

    @patch('cabot.cabotapp.models.send_alert')
    def test_critical_to_critical_inside_interval(self, fake_alert):
        """If ALERT_INTERVAL has not passed, critical -> critical should alert"""
        self.service.update_status()
        self.service.overall_status = Service.CRITICAL_STATUS
        self.service.old_overall_status = Service.CRITICAL_STATUS
        self.service.last_alert_sent = timezone.now()
        self.service.save()
        self.service.alert()
        self.assertFalse(fake_alert.called)
