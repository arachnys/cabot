from django.conf import settings

def google_clientid(request):
    return { 'GOOGLE_OAUTH2_CLIENT_ID': settings.GOOGLE_OAUTH2_CLIENT_ID }
