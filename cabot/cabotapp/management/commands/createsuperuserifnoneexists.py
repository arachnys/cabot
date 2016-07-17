#!/usr/bin/python
# A simple script to create a super user if one doesn't already exist.

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.six.moves import input
from django.core.management import call_command

class Command(BaseCommand):

    def handle(self, *args, **options):
        User = get_user_model()

        if not User.objects.filter(is_superuser=True).count():
            msg = ("\nCabot doesn't have any super users defined.\n\n"
                   "Would you like to create one now? (yes/no): ")
            confirm = input(msg)
            while 1:
                if confirm not in ('yes', 'no'):
                    confirm = input('Please enter either "yes" or "no": ')
                    continue
                if confirm == 'yes':
                    call_command("createsuperuser", interactive=True)
                break

