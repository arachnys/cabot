
import json

from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.template import Context, Template

from twilio.rest import TwilioRestClient
from twilio import twiml
import requests
import logging

logger = logging.getLogger(__name__)

email_template = """Service {{ service.name }} {{ scheme }}://{{ host }}{% url 'service' pk=service.id %} {% if service.overall_status != service.PASSING_STATUS %}alerting with status: {{ service.overall_status }}{% else %}is back to normal{% endif %}.
{% if service.overall_status != service.PASSING_STATUS %}
CHECKS FAILING:{% for check in service.all_failing_checks %}
  FAILING - {{ check.name }} - Type: {{ check.check_category }} - Importance: {{ check.get_importance_display }}{% endfor %}
{% if service.all_passing_checks %}
Passing checks:{% for check in service.all_passing_checks %}
  PASSING - {{ check.name }} - Type: {{ check.check_category }} - Importance: {{ check.get_importance_display }}{% endfor %}
{% endif %}
{% endif %}
"""

chat_template = "Service {{ service.name }} {% if service.overall_status == service.PASSING_STATUS %}is back to normal{% else %}reporting {{ service.overall_status }} status{% endif %}: {{ scheme }}://{{ host }}{% url 'service' pk=service.id %}. {% if service.overall_status != service.PASSING_STATUS %}Checks failing:{% for check in service.all_failing_checks %} {{ check.name }}{% if check.last_result.error %} ({{ check.last_result.error|safe }}){% endif %}{% endfor %}{% endif %}{% if alert %}{% for alias in users %} @{{ alias }}{% endfor %}{% endif %}"

sms_template = "Service {{ service.name }} {% if service.overall_status == service.PASSING_STATUS %}is back to normal{% else %}reporting {{ service.overall_status }} status{% endif %}: {{ scheme }}://{{ host }}{% url 'service' pk=service.id %}"

telephone_template = "This is an urgent message from Arachnys monitoring. Service \"{{ service.name }}\" is erroring. Please check Cabot urgently."


def send_alert(service, duty_officers=None):
    users = service.users_to_notify.filter(is_active=True)
    if service.email_alert:
        send_email_alert(service, users, duty_officers)
    if service.hipchat_alert:
        send_chat_alert('hipchat', service, users, duty_officers)
    if service.slack_alert:
        send_chat_alert('slack', service, users, duty_officers)
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


def send_chat_alert(chat_type, service, users, duty_officers):
    alert = True
    aliases = [
        getattr(u.profile, '%s_alias' % chat_type) for u in users
        if hasattr(u, 'profile') and hasattr(u.profile, '%s_alias' % chat_type)
    ]
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
            aliases += [
                getattr(u.profile, '%s_alias' % chat_type) for u in duty_officers
                if hasattr(u, 'profile') and hasattr(u.profile, '%s_alias' % chat_type)
            ]
    c = Context({
        'service': service,
        'users': aliases,
        'host': settings.WWW_HTTP_HOST,
        'scheme': settings.WWW_SCHEME,
        'alert': alert,
    })
    message = Template(chat_template).render(c)
    _send_chat_alert(chat_type, message, color=color, sender='Cabot/%s' % service.name)


def _send_chat_alert(chat_type, message, color='green', sender='Cabot'):
    if chat_type == 'hipchat':
        _send_hipchat_alert(message, color, sender)
    else:
        icon_url = settings.SLACK_ICON_URL
        _send_slack_alert(message, icon_url, sender)


def _send_hipchat_alert(message, color='green', sender='Cabot'):
    room = settings.HIPCHAT_ALERT_ROOM
    api_key = settings.HIPCHAT_API_KEY
    url = settings.HIPCHAT_URL
    requests.post(url + '?auth_token=' + api_key, data={
        'room_id': room,
        'from': sender[:15],
        'message': message,
        'notify': 1,
        'color': color,
        'message_format': 'text',
    })


def _send_slack_alert(message, icon_url, sender='Cabot'):
    room = settings.SLACK_ALERT_ROOM
    api_key = settings.SLACK_API_KEY
    url = settings.SLACK_URL
    logger.info('%s?token=%s' % (url, api_key))
    requests.post('%s?token=%s' % (url, api_key), data=json.dumps({
        'channel': room,
        'username': sender,
        'text': message,
        'icon_url': icon_url
    }))


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
