import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError


class Command(BaseCommand):
    def handle(self, *args, **options):
        username = os.environ.get('CABOT_SUPERUSER_USERNAME')
        if username:
            try:
                get_user_model().objects.create_superuser(
                    username=username,
                    email=os.environ.get('CABOT_SUPERUSER_EMAIL'),
                    password=os.environ.get('CABOT_SUPERUSER_PASSWORD')
                )
                print('Created superuser "{}"'.format(username))

            except IntegrityError:
                print('Superuser "{}" already exists'.format(username))
        else:
            print('CABOT_SUPERUSER_USERNAME environment variable not found, not creating superuser')
