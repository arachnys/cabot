# These views are here for legacy reasons. Cabot had several default StatusCheck
# types before the plugin system was implemented which had API urls located at the
# root of the API. These are emulated here so those that relied on the previous
# API urls can continue to use the API in an identical manner.
from cabot.cabotapp.models import StatusCheck
from cabot.plugins.models import StatusCheckPluginModel

from .views import StatusCheckViewSet

def create_legacy_check_viewset(plugin_slug):

    class LegacyStatusCheckViewSet(StatusCheckViewSet):

        def __init__(self, *args, **kwargs):
            ret = super(LegacyStatusCheckViewSet, self).__init__(*args, **kwargs)
            self.__class__.__name__ = self.get_status_check_plugin().full_name

            return ret

        def get_queryset(self, plugin_slug=plugin_slug):
            return StatusCheck.objects.filter(check_plugin__slug=plugin_slug)

        def get_status_check_plugin(self, plugin_slug=plugin_slug):
            return StatusCheckPluginModel.objects.get(slug=plugin_slug)

        def create(self, request, plugin_slug=plugin_slug):
            mod_req = request
            mod_req.data['check_plugin'] = plugin_slug
            
            return super(LegacyStatusCheckViewSet, self).create(mod_req)
    
    return LegacyStatusCheckViewSet

HttpStatusCheckViewSet = create_legacy_check_viewset('cabot_check_http')
GraphiteStatusCheckViewSet = create_legacy_check_viewset('cabot_check_graphite')
JenkinsStatusCheckViewSet= create_legacy_check_viewset('cabot_check_jenkins')
ICMPStatusCheckViewSet = create_legacy_check_viewset('cabot_check_icmp')

