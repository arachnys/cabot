from django import template
from django.conf import settings
from datetime import timedelta
from cabot.cabotapp.models import StatusCheck, Instance, Service
from cabot.plugins.models import AlertPluginModel, StatusCheckPluginModel
register = template.Library()


@register.simple_tag
def jenkins_human_url(jobname):
    return '{}job/{}/'.format(settings.JENKINS_API, jobname)


@register.simple_tag
def echo_setting(setting):
    return getattr(settings, setting, '')

@register.filter(name='format_timedelta')
def format_timedelta(delta):
    # Getting rid of microseconds.
    return str(timedelta(days=delta.days, seconds=delta.seconds))

@register.inclusion_tag('cabotapp/_statuscheck_list.html')
def print_status_checks(check_owner, check_plugin):
    return {
        'check_plugin': check_plugin,
        'checks': check_owner.status_checks.filter(check_plugin=check_plugin),
        'service': check_owner if isinstance(check_owner, Service) else None,
        'instance': check_owner if isinstance(check_owner, Instance) else None
    }
    
