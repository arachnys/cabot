from django import template
from django.conf import settings
from datetime import timedelta
from urlparse import urljoin

register = template.Library()


@register.simple_tag
def jenkins_human_url(jobname):
    return urljoin(settings.JENKINS_API, 'job/{}/'.format(jobname))


@register.filter(name='format_timedelta')
def format_timedelta(delta):
    # Getting rid of microseconds.
    return str(timedelta(days=delta.days, seconds=delta.seconds))


@register.filter
def get_index(obj, key):
    """
    This is for doing obj[key] in a Django template, which incredibly doesn't work
    See https://stackoverflow.com/questions/8000022/django-template-how-to-look-up-a-dictionary-value-with-a-variable
    """
    return obj[key]
