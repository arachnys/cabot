from django.conf import settings


def build_absolute_url(relative_url):
    """Prepend https?://host to a url, useful for links going into emails"""
    return '{}://{}{}'.format(settings.WWW_SCHEME, settings.WWW_HTTP_HOST, relative_url)
