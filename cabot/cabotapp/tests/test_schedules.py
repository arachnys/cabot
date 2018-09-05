import os

from django.contrib.auth.models import User
from datetime import datetime

from django.core.urlresolvers import reverse
from django.utils import timezone
from mock import patch

from cabot.cabotapp import tasks
from cabot.cabotapp.models import (
    get_duty_officers,
    get_all_duty_officers,
    update_shifts, Schedule)
from cabot.cabotapp.utils import build_absolute_url
from cabot.metricsapp.defs import SCHEDULE_PROBLEMS_EMAIL_SNOOZE_HOURS
from .utils import LocalTestCase, fake_calendar


def _create_fake_users(usernames):
    """Create fake Users with the listed usernames"""
    for user in usernames:
        User.objects.create(
            username=user[:30],
            password='fakepassword',
            email=user,
            is_active=True,
        )


def _snooze_url(schedule, hours):
    return build_absolute_url(reverse('snooze-schedule-warnings', kwargs={
        'pk': schedule.pk, 'hours': hours,
    }))


class TestSchedules(LocalTestCase):
    def setUp(self):
        super(TestSchedules, self).setUp()
        _create_fake_users([
            'dolores@affirm.com',
            'bernard@affirm.com',
            'teddy@affirm.com',
            'maeve@affirm.com',
            'hector@affirm.com',
            'armistice@affirm.com',
            'longnamelongnamelongnamelongname@affirm.com',
            'shortname@affirm.com',
        ])

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    def test_single_schedule(self):
        """
        Make sure the correct person is marked as a duty officer
        if there's a single calendar
        """
        # initial user plus new 8
        self.assertEqual(len(User.objects.all()), 9)

        update_shifts(self.schedule)

        officers = get_duty_officers(self.schedule, at_time=datetime(2016, 11, 6, 0, 0, 0))
        usernames = [str(user.username) for user in officers]
        self.assertEqual(usernames, ['dolores@affirm.com'])

        officers = get_duty_officers(self.schedule, at_time=datetime(2016, 11, 8, 0, 0, 0))
        usernames = [str(user.username) for user in officers]
        self.assertEqual(usernames, ['teddy@affirm.com'])

        officers = get_duty_officers(self.schedule, at_time=datetime(2016, 11, 8, 10, 0, 0))
        usernames = [str(user.username) for user in officers]
        self.assertEqual(usernames, ['teddy@affirm.com'])

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    def test_update_schedule_twice(self):
        """Make sure nothing changes if you update twice"""
        for _ in range(2):
            update_shifts(self.schedule)
            officers = get_duty_officers(self.schedule, at_time=datetime(2016, 11, 6, 0, 0, 0))
            usernames = [str(user.username) for user in officers]
            self.assertEqual(usernames, ['dolores@affirm.com'])

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    def test_multiple_schedules(self):
        """
        Add a second calendar and make sure the correct duty officers are marked
        for each calendar
        """
        self.assertEqual(len(User.objects.all()), 9)

        update_shifts(self.secondary_schedule)
        update_shifts(self.schedule)

        officers = get_duty_officers(self.secondary_schedule, at_time=datetime(2016, 11, 6, 0, 0, 0))
        usernames = [str(user.username) for user in officers]
        self.assertEqual(usernames, ['maeve@affirm.com'])

        old_officers = get_duty_officers(self.schedule, at_time=datetime(2016, 11, 6, 0, 0, 0))
        old_usernames = [user.username for user in old_officers]
        self.assertEqual(old_usernames, ['dolores@affirm.com'])

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    def test_get_all_duty_officers(self):
        """
        Make sure get_all_duty_officers works with multiple calendars
        """
        self.assertEqual(len(User.objects.all()), 9)

        update_shifts(self.schedule)
        update_shifts(self.secondary_schedule)

        officers_dict = get_all_duty_officers(at_time=datetime(2016, 11, 6, 0, 0, 0))
        officers = []
        for item in officers_dict.iteritems():
            officers.append(item)

        self.assertEqual(len(officers), 2)

        officer_schedule = [(officers[0][0].username, officers[0][1][0].name),
                            (officers[1][0].username, officers[1][1][0].name)]
        self.assertIn(('dolores@affirm.com', 'Principal'), officer_schedule)
        self.assertIn(('maeve@affirm.com', 'Secondary'), officer_schedule)

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    def test_calendar_update_remove_oncall(self):
        """
        Test that an oncall officer gets removed if they aren't on the schedule
        """
        update_shifts(self.schedule)

        officers = get_duty_officers(self.schedule, at_time=datetime(2016, 11, 8, 10, 0, 0))
        usernames = [str(user.username) for user in officers]
        self.assertEqual(usernames, ['teddy@affirm.com'])

        # Change the schedule
        self.schedule.ical_url = 'calendar_response_different.ics'
        self.schedule.save()
        update_shifts(self.schedule)

        officers = get_duty_officers(self.schedule, at_time=datetime(2016, 11, 8, 10, 0, 0))
        usernames = [str(user.username) for user in officers]
        self.assertEqual(usernames, ['hector@affirm.com'])

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    def test_calendar_long_name(self):
        """
        Test that we can sync oncall schedules for users with emails > 30 characters
        """
        self.schedule.ical_url = 'calendar_response_long_name.ics'
        self.schedule.save()
        update_shifts(self.schedule)

        officers = get_duty_officers(self.schedule, at_time=datetime(2016, 11, 7, 10, 0, 0))
        emails = [str(user.email) for user in officers]
        self.assertEqual(emails, ['longnamelongnamelongnamelongname@affirm.com'])


class TestScheduleValidation(LocalTestCase):
    def setUp(self):
        super(TestScheduleValidation, self).setUp()

        _create_fake_users([
            'dolores@affirm.com',
            'bernard@affirm.com',
            'teddy@affirm.com',
            'maeve@affirm.com',
            'hector@affirm.com',
            'armistice@affirm.com',
            'longnamelongnamelongnamelongname@affirm.com',
            'shortname@affirm.com',
        ])

        self.secondary_schedule.delete()
        self.secondary_schedule = None

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    @patch('cabot.cabotapp.tasks.send_mail')
    @patch('cabot.cabotapp.models.timezone.now')
    def test_validate_schedule_no_gaps(self, fake_now, fake_send_mail):
        fake_now.return_value = datetime(2018, 8, 15, 0, 3, 54, 598552, tzinfo=timezone.utc)

        self.schedule.ical_url = 'calendar_no_gaps.ics'
        self.schedule.fallback_officer = User.objects.get(email='dolores@affirm.com')
        self.schedule.save()
        tasks.update_shifts_and_problems()  # simulate periodic task firing
        self.schedule = Schedule.objects.get(pk=self.schedule.pk)  # refresh from DB

        self.assertFalse(fake_send_mail.called)
        self.assertFalse(self.schedule.has_problems())

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    @patch('cabot.cabotapp.tasks.send_mail')
    @patch('cabot.cabotapp.models.timezone.now')
    def test_validate_schedule_with_gaps(self, fake_now, fake_send_mail):
        fake_now.return_value = datetime(2018, 8, 15, 0, 3, 54, 598552, tzinfo=timezone.utc)

        self.schedule.ical_url = 'calendar_with_gaps.ics'
        self.schedule.fallback_officer = User.objects.filter(email='dolores@affirm.com').first()
        self.schedule.save()
        tasks.update_shifts_and_problems()  # simulate periodic task firing
        self.schedule = Schedule.objects.get(pk=self.schedule.pk)  # refresh from DB

        self.assertEqual(SCHEDULE_PROBLEMS_EMAIL_SNOOZE_HOURS, [4, 12, 24])  # this test is hard-coded for 4/12/24
        message = """\
The schedule <a href="{edit_schedule_url}">Principal</a> has some issues:

There are gaps in the schedule (times are UTC):
* 2018-08-17 19:00:00 to 2018-08-18 19:00:00 (1d)
* 2018-08-19 19:00:00 to 2018-08-20 19:00:00 (1d)

Click <a href="{edit_schedule_url}">here</a> to review the schedule\'s configuration.
If you don\'t want to deal with this right now, you can silence these alerts for \
<a href="{}">4 hours</a> | <a href="{}">12 hours</a> | <a href="{}">24 hours</a>.""" \
            .format(_snooze_url(self.schedule, 4), _snooze_url(self.schedule, 12), _snooze_url(self.schedule, 24),
                    edit_schedule_url=build_absolute_url(reverse('update-schedule', kwargs={'pk': self.schedule.pk})))

        address = os.environ.get('CABOT_FROM_EMAIL')
        # should email dolores (fallback officer) and teddy (on call)
        fake_send_mail.assert_called_once_with(subject="Cabot Schedule 'Principal' Has Problems",
                                               message=message,
                                               from_email='Cabot Updates<{}>'.format(address),
                                               recipient_list=[u'teddy@affirm.com', u'dolores@affirm.com'])

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    @patch('cabot.cabotapp.models.timezone.now')
    def test_validate_schedule_problems_fixed(self, fake_now):
        """Test that schedule.problems gets set then cleared after we fix the problems"""

        fake_now.return_value = datetime(2018, 8, 15, 0, 3, 54, 598552, tzinfo=timezone.utc)

        # start with 2 problems
        self.schedule.ical_url = 'calendar_with_gaps.ics'  # bad calendar
        self.schedule.fallback_officer = None  # no fallback officer
        self.schedule.save()
        # update_shifts() and update_problems() automatically called by post_save handler
        self.schedule = Schedule.objects.get(pk=self.schedule.pk)  # refresh from DB

        # check that schedule.problems gets set correctly
        problems_str = """\
The schedule has no fallback officer.

There are gaps in the schedule (times are UTC):
* 2018-08-17 19:00:00 to 2018-08-18 19:00:00 (1d)
* 2018-08-19 19:00:00 to 2018-08-20 19:00:00 (1d)\
"""
        self.assertEquals(self.schedule.problems.text, problems_str)

        # change the calendar to a valid one (still no fallback officer)
        self.schedule.ical_url = 'calendar_no_gaps.ics'
        self.schedule.save()
        # update_shifts() and update_problems() automatically called by post_save handler
        self.schedule = Schedule.objects.get(pk=self.schedule.pk)  # refresh from DB

        self.assertEquals(self.schedule.problems.text, "The schedule has no fallback officer.")

        # fix the fallback officer (now there are no problems)
        self.schedule.fallback_officer = User.objects.filter(email='dolores@affirm.com').first()
        self.schedule.save()
        # update_shifts(self.schedule) and self.schedule.update_problems() automatically called by post_save handler
        self.schedule = Schedule.objects.get(pk=self.schedule.pk)  # refresh from DB

        # verify that problems got cleared
        self.assertFalse(self.schedule.has_problems())

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    @patch('cabot.cabotapp.tasks.send_mail')
    @patch('cabot.cabotapp.models.timezone.now')
    def test_validate_schedule_silence_emails_until(self, fake_now, fake_send_mail):
        """Verify that schedule warning emails don't get sent during the silence_warnings_until window"""
        fake_now.return_value = datetime(2018, 8, 15, 0, 3, 54, 598552, tzinfo=timezone.utc)

        self.schedule.ical_url = 'calendar_with_gaps.ics'  # bad calendar
        self.schedule.fallback_officer = User.objects.get(email='dolores@affirm.com')
        self.schedule.save()  # calls update_shifts() and update_problems() via celery task

        # silence for 1 hour
        self.schedule.problems.silence_warnings_until = datetime(2018, 8, 15, 1, 3, 54, 598552, tzinfo=timezone.utc)
        self.schedule.problems.save()

        self.schedule = Schedule.objects.get(pk=self.schedule.pk)  # refresh from DB
        self.assertTrue(self.schedule.problems.is_silenced())

        tasks.update_shifts_and_problems()  # simulate periodic task firing (which sends emails)
        self.assertFalse(fake_send_mail.called)

        # after an hour and 1 minute, check that warning emails now get sent
        fake_send_mail.reset_mock()
        fake_now.return_value = datetime(2018, 8, 15, 1, 4, 54, 598552, tzinfo=timezone.utc)
        tasks.update_shifts_and_problems()  # simulate periodic task firing
        self.schedule = Schedule.objects.get(pk=self.schedule.pk)  # refresh from DB
        self.assertTrue(fake_send_mail.called)
        self.assertFalse(self.schedule.problems.is_silenced())

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    @patch('cabot.cabotapp.models.timezone.now')
    def test_validate_schedule_ui_shows_problems(self, fake_now):
        fake_now.return_value = datetime(2018, 8, 15, 0, 3, 54, 598552, tzinfo=timezone.utc)

        # check that the UI doesn't show any problems
        response = self.client.get(reverse('shifts'))
        self.assertNotContains(response, "Problems", status_code=200)

        self.schedule.ical_url = 'calendar_with_gaps.ics'  # bad calendar
        self.schedule.fallback_officer = User.objects.filter(email='dolores@affirm.com').first()
        self.schedule.save()  # calls update_shifts() and update_problems() via celery task
        self.schedule = Schedule.objects.get(pk=self.schedule.pk)  # refresh from DB

        # check that the UI now shows problems
        response = self.client.get(reverse('shifts'))
        self.assertContains(response, "Problems", status_code=200)

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    @patch('cabot.cabotapp.models.timezone.now')
    def test_validate_schedule_ui_shows_problems_while_silenced(self, fake_now):
        fake_now.return_value = datetime(2018, 8, 15, 0, 3, 54, 598552, tzinfo=timezone.utc)

        # check that the UI doesn't show any problems
        response = self.client.get(reverse('shifts'))
        self.assertNotContains(response, "Problems", status_code=200)

        # make the schedule "bad"
        self.schedule.ical_url = 'calendar_with_gaps.ics'  # bad calendar
        self.schedule.fallback_officer = User.objects.get(email='dolores@affirm.com')
        self.schedule.save()  # calls update_shifts() and update_problems() via post_save handler

        # silence through the UI
        self.client.get(reverse('snooze-schedule-warnings', kwargs={'pk': self.schedule.pk, 'hours': 1}))

        # check that the UI still shows "Problems" even though emails are silenced
        response = self.client.get(reverse('shifts'))
        self.assertContains(response, "Problems", status_code=200)
        self.assertContains(response, "Emails about these problems are silenced until", status_code=200)
        self.assertContains(response, "label-warning", status_code=200)  # check color-coding (a bit fragile...)

    @patch('cabot.cabotapp.models.requests.get', fake_calendar)
    @patch('cabot.cabotapp.tasks.send_mail')
    @patch('cabot.cabotapp.models.timezone.now')
    def test_validate_schedule_lots_of_gaps(self, fake_now, fake_send_mail):
        """Make sure a schedule with a ton of gaps doesn't make a super long message"""

        fake_now.return_value = datetime(2018, 8, 15, 0, 3, 54, 598552, tzinfo=timezone.utc)

        self.schedule.ical_url = 'calendar_with_lots_of_gaps.ics'
        self.schedule.fallback_officer = User.objects.filter(email='dolores@affirm.com').first()
        self.schedule.save()
        tasks.update_shifts_and_problems()  # periodic task that sends emails
        self.schedule = Schedule.objects.get(pk=self.schedule.pk)  # refresh from DB

        problems = """\
There are gaps in the schedule (times are UTC):
* 2018-08-15 00:03:54.598552 to 2018-08-21 17:53:28 (6d, 17h, 49m, 33s)
* 2018-08-21 23:45:16 to 2018-08-22 07:00:00 (7h, 14m, 44s)
* 2018-08-22 08:00:00 to 2018-08-23 07:00:00 (23h)
* 2018-08-23 08:00:00 to 2018-08-24 07:00:00 (23h)
* 2018-08-24 08:00:00 to 2018-08-25 07:00:00 (23h)
(Plus another 182 gap(s) not listed here.)"""

        self.assertTrue(fake_send_mail.called)
        self.assertEqual(self.schedule.problems.text, problems)
