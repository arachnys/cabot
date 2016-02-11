from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
import os


class Command(BaseCommand):
    help = 'Automatically create superuser based on environment variables.'

    def handle(self, *args, **options):
        email = os.getenv('CABOT_ADMIN_EMAIL')
        username = os.getenv('CABOT_ADMIN_USERNAME')
        password = os.getenv('CABOT_ADMIN_PASSWORD')

        u = User(username=username, email=email)
        u.set_password(password)
        u.is_superuser = True
        u.is_staff = True
        u.save()
