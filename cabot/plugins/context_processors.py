from cabot.plugins.models import StatusCheckPluginModel

def check_plugins(request):
    if not request.user.is_authenticated():
        return dict()
    else:
        return {'all_check_plugins': StatusCheckPluginModel.objects.all()}

