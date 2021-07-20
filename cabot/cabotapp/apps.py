from django.apps import AppConfig
from django.db.models.signals import post_migrate


def post_migrate_callback(**kwargs):
    from cabot.cabotapp.alert import update_alert_plugins
    update_alert_plugins()
    

class CabotappConfig(AppConfig):
    name = 'cabot.cabotapp'

    def ready(self):
        post_migrate.connect(post_migrate_callback, sender=self)
