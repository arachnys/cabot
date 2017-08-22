import logging

from django.db import models
from polymorphic import PolymorphicModel

logger = logging.getLogger(__name__)


class AlertPlugin(PolymorphicModel):
    title = models.CharField(max_length=30, unique=True, editable=False)
    enabled = models.BooleanField(default=True)

    author = None
    # Plugins use name field
    name = 'noop'

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


def send_alert(service, duty_officers=[], fallback_officers=[]):
    users = service.users_to_notify.filter(is_active=True)
    for alert in service.alerts.all():
        try:
            alert.send_alert(service, users, duty_officers)
        except Exception as e:
            logging.exception('Could not sent {} alert'.format(alert.name))
            if fallback_officers:
                try:
                    alert.send_alert(service, users, fallback_officers)
                except Exception:
                    logging.exception('Could not send {} alert to fallback officer'.format(alert.name))


def update_alert_plugins():
    for plugin_subclass in AlertPlugin.__subclasses__():
        plugin_subclass.objects.get_or_create(title=plugin_subclass.name)
    return AlertPlugin.objects.all()
