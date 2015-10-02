from os import environ as env

from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.template import Context, Template
from django.db import models
from django.db.models import get_models

from twilio.rest import TwilioRestClient
from twilio import twiml

import requests
import logging
import re

from polymorphic import PolymorphicModel

logger = logging.getLogger(__name__)

class AlertPlugin(PolymorphicModel):
    title = models.CharField(max_length=30, unique=True, editable=False)
    enabled = models.BooleanField(default=True)

    author = None

    def __unicode__(self):
        return u'%s' % (self.title)

    def send_alert(self, service, users, duty_officers):
        """
        Implement a send_alert function here that shall be called.
        """
        return True

class AlertPluginUserData(PolymorphicModel):
    title = models.CharField(max_length=30, editable=False)
    user = models.ForeignKey('UserProfile', editable=False)

    class Meta:
        unique_together = ('title', 'user',)

    def __unicode__(self):
        return u'%s' % (self.title)

def send_alert(service, duty_officers=None):
    users = service.users_to_notify.filter(is_active=True)
    for alert in service.alerts.all():
        try:
            alert.send_alert(service, users, duty_officers)
        except Exception as e:
            logging.exception('Could not send %s alert: %s' % (alert.name, e))

def send_alert_update(service, duty_officers=None):
    users = service.users_to_notify.filter(is_active=True)
    for alert in service.alerts.all():
        if hasattr(alert, 'send_alert_update'):
            try:
                alert.send_alert_update(service, users, duty_officers)
            except Exception as e:
                logger.exception('Could not send %s alert update: %s' % (alert.name, e))
        else:
            logger.warning('No send_alert_update method present for %s' % alert.name)


def update_alert_plugins():
    for plugin_subclass in AlertPlugin.__subclasses__():
        plugin = plugin_subclass.objects.get_or_create(title=plugin_subclass.name)
    return AlertPlugin.objects.all()
