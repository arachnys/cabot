from django.apps import AppConfig
from django.db.models.signals import post_migrate


def post_migrate_callback(**kwargs):
    from cabot.cabotapp.alert import update_alert_plugins
    from cabot.cabotapp.models import create_default_jenkins_config
    update_alert_plugins()
    create_default_jenkins_config()

class CabotappConfig(AppConfig):
    name = 'cabot.cabotapp'

    def ready(self):
        post_migrate.connect(post_migrate_callback, sender=self)
