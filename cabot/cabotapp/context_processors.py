from cabot.cabotapp.checks import CheckPlugin

def navbar_processor(request):
	check_plugins = CheckPlugin.objects.all()
	return {'check_plugins': check_plugins}