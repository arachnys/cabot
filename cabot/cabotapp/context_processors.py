from cabot.cabotapp.checks import CheckPlugin

def navbar_processor(request):
	check_plugins = CheckPlugin.__subclasses__()
	return {'check_plugins': check_plugins}