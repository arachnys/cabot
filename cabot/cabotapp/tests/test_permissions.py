from cabot.cabotapp.tests.tests_basic import LocalTestCase

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.reverse import reverse as api_reverse


class TestUserPermissions(LocalTestCase):

    def setUp(self):
        super(TestUserPermissions, self).setUp()
        self.user1 = User.objects.create_user(username='user1', password='pass1')
        self.user2 = User.objects.create_user(username='user2', password='pass2')
        self.user2.is_superuser = True
        self.user2.save()

    def test_user_profile_normal_permissions(self):
        self.client.login(username='user1', password='pass1')
        response = self.client.get(
            api_reverse('update-alert-user-data', kwargs={'pk': self.user1.pk, 'alerttype': 'General'}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(
            api_reverse('update-alert-user-data', kwargs={'pk': self.user2.pk, 'alerttype': 'General'}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_profile_superuser_permissions(self):
        self.client.login(username='user2', password='pass2')
        response = self.client.get(
            api_reverse('update-alert-user-data', kwargs={'pk': self.user1.pk, 'alerttype': 'General'}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(
            api_reverse('update-alert-user-data', kwargs={'pk': self.user2.pk, 'alerttype': 'General'}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
