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
