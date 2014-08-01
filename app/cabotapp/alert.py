from os import environ as env

from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.template import Context, Template

from twilio.rest import TwilioRestClient
from twilio import twiml
import requests
import logging

logger = logging.getLogger(__name__)

email_template = """Service {{ service.name }} {{ scheme }}://{{ host }}{% url service pk=service.id %} {% if service.overall_status != service.PASSING_STATUS %}alerting with status: {{ service.overall_status }}{% else %}is back to normal{% endif %}.
{% if service.overall_status != service.PASSING_STATUS %}
CHECKS FAILING:{% for check in service.all_failing_checks %}
  FAILING - {{ check.name }} - Type: {{ check.check_category }} - Importance: {{ check.get_importance_display }}{% endfor %}
{% if service.all_passing_checks %}
Passing checks:{% for check in service.all_passing_checks %}
  PASSING - {{ check.name }} - Type: {{ check.check_category }} - Importance: {{ check.get_importance_display }}{% endfor %}
{% endif %}
{% endif %}
"""

hipchat_template = "Service {{ service.name }} {% if service.overall_status == service.PASSING_STATUS %}is back to normal{% else %}reporting {{ service.overall_status }} status{% endif %}: {{ scheme }}://{{ host }}{% url service pk=service.id %}. {% if service.overall_status != service.PASSING_STATUS %}Checks failing:{% for check in service.all_failing_checks %} {{ check.name }}{% if check.last_result.error %} ({{ check.last_result.error|safe }}){% endif %}{% endfor %}{% endif %}{% if alert %}{% for alias in users %} @{{ alias }}{% endfor %}{% endif %}"

pushover_template = """{% if service.overall_status != service.PASSING_STATUS %}{% for check in service.all_failing_checks %}[{{ check.importance }}] {{ check.name.upper }} failed{% if check.last_result.error %} ({{ check.last_result.error|safe }}).{% if check.check_category == 'HTTP check' %} Raw: {{ check.last_result.raw_data|slice:':40' }}{% endif %}{% endif %}\n{% endfor %}{% else %}Service recovered. All checks passing.{% endif %}"""

sms_template = "Service {{ service.name }} {% if service.overall_status == service.PASSING_STATUS %}is back to normal{% else %}reporting {{ service.overall_status }} status{% endif %}: {{ scheme }}://{{ host }}{% url service pk=service.id %}"

telephone_template = "This is an urgent message from Arachnys monitoring. Service \"{{ service.name }}\" is erroring. Please check Cabot urgently."


def send_alert(service, duty_officers=None):
    users = service.users_to_notify.all()
    if service.email_alert:
        send_email_alert(service, users, duty_officers)
    if service.hipchat_alert:
        send_hipchat_alert(service, users, duty_officers)
    if service.pushover_alert:
        send_pushover_alert(service, users, duty_officers)
    if service.sms_alert:
        send_sms_alert(service, users, duty_officers)
    if service.telephone_alert:
        send_telephone_alert(service, users, duty_officers)


def send_email_alert(service, users, duty_officers):
    emails = [u.email for u in users if u.email]
    if not emails:
        return
    c = Context({
        'service': service,
        'host': settings.WWW_HTTP_HOST,
        'scheme': settings.WWW_SCHEME
    })
    if service.overall_status != service.PASSING_STATUS:
        if service.overall_status == service.CRITICAL_STATUS:
            emails += [u.email for u in duty_officers]
        subject = '%s status for service: %s' % (
            service.overall_status, service.name)
    else:
        subject = 'Service back to normal: %s' % (service.name,)
    t = Template(email_template)
    send_mail(
        subject=subject,
        message=t.render(c),
        from_email='Cabot <%s>' % settings.CABOT_FROM_EMAIL,
        recipient_list=emails,
    )


def send_hipchat_alert(service, users, duty_officers):
    alert = True
    hipchat_aliases = [u.profile.hipchat_alias for u in users if hasattr(
        u, 'profile') and u.profile.hipchat_alias]
    if service.overall_status == service.WARNING_STATUS:
        alert = False  # Don't alert at all for WARNING
    if service.overall_status == service.ERROR_STATUS:
        if service.old_overall_status in (service.ERROR_STATUS, service.ERROR_STATUS):
            alert = False  # Don't alert repeatedly for ERROR
    if service.overall_status == service.PASSING_STATUS:
        color = 'green'
        if service.old_overall_status == service.WARNING_STATUS:
            alert = False  # Don't alert for recovery from WARNING status
    else:
        color = 'red'
        if service.overall_status == service.CRITICAL_STATUS:
            hipchat_aliases += [u.profile.hipchat_alias for u in duty_officers if hasattr(
                u, 'profile') and u.profile.hipchat_alias]
    c = Context({
        'service': service,
        'users': hipchat_aliases,
        'host': settings.WWW_HTTP_HOST,
        'scheme': settings.WWW_SCHEME,
        'alert': alert,
    })
    message = Template(hipchat_template).render(c)
    _send_hipchat_alert(message, color=color, sender='Cabot/%s' % service.name)


def _send_hipchat_alert(message, color='green', sender='Cabot'):
    room = settings.HIPCHAT_ALERT_ROOM
    api_key = settings.HIPCHAT_API_KEY
    url = settings.HIPCHAT_URL
    resp = requests.post(url + '?auth_token=' + api_key, data={
        'room_id': room,
        'from': sender[:15],
        'message': message,
        'notify': 1,
        'color': color,
        'message_format': 'text',
    })

def send_pushover_alert(service, users, duty_officers):
    title= ''
    priority = 0
    pushover_keys = [u.profile.pushover_key for u in users if hasattr(
        u, 'profile') and u.profile.pushover_key]

    if service.overall_status == service.WARNING_STATUS:
        title= u'\u26A0\ufe0f '
    elif service.overall_status == service.PASSING_STATUS:
        title= u'\u2705 '
        if service.old_overall_status == service.WARNING_STATUS:
          priority -= 1  # Don't alert for recovery from WARNING status
    else:
        title= u'\u274C '
        priority += 1
        if service.overall_status == service.CRITICAL_STATUS:
          pushover_keys += [u.profile.pushover_key for u in duty_officers if hasattr(
                u, 'profile') and u.profile.pushover_key]

    c = Context({
        'service': service,
        'host': settings.WWW_HTTP_HOST,
        'scheme': settings.WWW_SCHEME,
    })

    message = Template(pushover_template).render(c)
    title += service.name
    url= Template('{{ scheme }}://{{ host }}{% url service pk=service.id %}').render(c)
    url_title= 'Show in Cabot'

    for key in pushover_keys:
      _send_pushover_alert(message, key, title, priority, url, url_title)


def _send_pushover_alert(message, user, title= None, priority=0, url= None, url_title=None):
    resp = requests.post(settings.PUSHOVER_URL, data={
        'token': settings.PUSHOVER_TOKEN,
        'user': user,
        'title': title,
        'message': message,
        'priority': priority,
        'url': url,
        'url_title': url_title,
    })

def send_sms_alert(service, users, duty_officers):
    client = TwilioRestClient(
        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    mobiles = [u.profile.prefixed_mobile_number for u in users if hasattr(
        u, 'profile') and u.profile.mobile_number]
    if service.is_critical:
        mobiles += [u.profile.prefixed_mobile_number for u in duty_officers if hasattr(
            u, 'profile') and u.profile.mobile_number]
    c = Context({
        'service': service,
        'host': settings.WWW_HTTP_HOST,
        'scheme': settings.WWW_SCHEME,
    })
    message = Template(sms_template).render(c)
    mobiles = list(set(mobiles))
    for mobile in mobiles:
        try:
            client.sms.messages.create(
                to=mobile,
                from_=settings.TWILIO_OUTGOING_NUMBER,
                body=message,
            )
        except Exception, e:
            logger.exception('Error sending twilio sms: %s' % e)


def send_telephone_alert(service, users, duty_officers):
    # No need to call to say things are resolved
    if service.overall_status != service.CRITICAL_STATUS:
        return
    client = TwilioRestClient(
        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    mobiles = [u.profile.prefixed_mobile_number for u in duty_officers if hasattr(
        u, 'profile') and u.profile.mobile_number]
    url = 'http://%s%s' % (settings.WWW_HTTP_HOST,
                           reverse('twiml-callback', kwargs={'service_id': service.id}))
    for mobile in mobiles:
        try:
            client.calls.create(
                to=mobile,
                from_=settings.TWILIO_OUTGOING_NUMBER,
                url=url,
                method='GET',
            )
        except Exception, e:
            logger.exception('Error making twilio phone call: %s' % e)


def telephone_alert_twiml_callback(service):
    c = Context({'service': service})
    t = Template(telephone_template).render(c)
    r = twiml.Response()
    r.say(t, voice='woman')
    r.hangup()
    return r
