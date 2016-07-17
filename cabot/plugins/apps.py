from django.apps import AppConfig
from django.conf import settings
from logging import getLogger
import importlib
import sys

logger = getLogger(__name__)

class PluginsConfig(AppConfig):

    name = "cabot.plugins"

    def ready(self):
        # Cheeky hack to skip plugin creation during migrations (as the
        # necessary tables may not have been created(.
        if any("migrat" in s.lower() for s in sys.argv):
            return

        # Run necessary imports
        from cabot.plugins.models import (
            AlertPlugin, AlertPluginModel, AlertPluginUserData,
            StatusCheckPlugin, StatusCheckPluginModel,
            FailedImport,
        )
        from django.contrib.auth.models import User

        # Delete all previous import errors
        FailedImport.objects.all().delete()

        # Import the plugins
        for plugin_name in settings.CABOT_PLUGINS_ENABLED_PARSED:
            try:
                importlib.import_module('{}.plugin'.format(plugin_name))
            except Exception as  e:
                logger.info('Failed to import plugin {}: {}'.format(plugin_name, str(e)))

                # Register the import errors in the Database.
                FailedImport.objects.create(
                    plugin_name = plugin_name,
                    error_message = str(e),
                )
        
        # Register the plugins with Cabot
        alert_plugins_available = [p.slug for p in AlertPlugin.__subclasses__()]
        for slug in alert_plugins_available:
            AlertPluginModel.objects.get_or_create(slug=slug)

        check_plugins_available = [p.slug for p in StatusCheckPlugin.__subclasses__()]
        for slug in check_plugins_available:
            StatusCheckPluginModel.objects.get_or_create(slug=slug)

