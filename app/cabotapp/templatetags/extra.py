from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def jenkins_human_url(jobname):
    return '{}job/{}/'.format(settings.JENKINS_API, jobname)
