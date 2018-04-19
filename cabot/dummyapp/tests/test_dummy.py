from django.contrib.auth.models import User
from django.test import TestCase
from cabot.dummyapp.models import DummySource, DummyStatusCheck


class TestDummyCheck(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('user')
        self.source = DummySource.objects.create(name='dumb')
        self.dummy_check = DummyStatusCheck(
            name='dummycheck',
            created_by=self.user,
            source=self.source,
            check_type='<',
            warning_value=500,
            high_alert_value=1500,
            high_alert_importance='CRITICAL',
            counter=0
        )

    def test_dummy(self):
        """
        Should alternate successes and failures, starting with success because
        counter is even
        """
        result = self.dummy_check._run()
        self.assertTrue(result.succeeded)
        self.assertIsNone(result.error)

        result = self.dummy_check._run()
        self.assertFalse(result.succeeded)
        self.assertEqual(result.error, 'WARNING dummy: 1000.0 not < 500.0')
        self.assertEqual(self.dummy_check.importance, 'WARNING')
