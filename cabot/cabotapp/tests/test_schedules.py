from django.contrib.auth.models import User
from datetime import datetime
from mock import patch
from cabot.cabotapp.models import (
    get_duty_officers,
    get_all_duty_officers,
    update_shifts,
)
from .utils import LocalTestCase, fake_calendar


class TestSchedules(LocalTestCase):
    def setUp(self):
        super(TestSchedules, self).setUp()
        self.create_fake_users([
            'dolores@affirm.com',
            'bernard@affirm.com',
            'teddy@affirm.com',
            'maeve@affirm.com',
            'hector@affirm.com',
            'armistice@affirm.com',
            'longnamelongnamelongnamelongname@affirm.com',
            'shortname@affirm.com',
        ])

    def create_fake_users(self, usernames):
        """Create fake Users with the listed usernames"""
        for user in usernames:
            User.objects.create(
                username=user[:30],
                password='fakepassword',
                email=user,
                is_active=True,
            )

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
