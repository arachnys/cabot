from django import template

from ..jenkins import get_jenkins_url

register = template.Library()

@register.simple_tag
def jenkins_url(jobname):
  return get_jenkins_url(jobname)
