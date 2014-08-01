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

email_template = """Instance {{ instance.name }} {{ scheme }}://{{ host }}{% url instance pk=instance.id %} {% if instance.overall_status != instance.PASSING_STATUS %}alerting with status: {{ instance.overall_status }}{% else %}is back to normal{% endif %}.
{% if instance.overall_status != instance.PASSING_STATUS %}
CHECKS FAILING:{% for check in instance.all_failing_checks %}
  FAILING - {{ check.name }} - Type: {{ check.check_category }} - Importance: {{ check.get_importance_display }}{% endfor %}
{% if instance.all_passing_checks %}
Passing checks:{% for check in instance.all_passing_checks %}
  PASSING - {{ check.name }} - Type: {{ check.check_category }} - Importance: {{ check.get_importance_display }}{% endfor %}
{% endif %}
{% endif %}
"""

hipchat_template = "Instance {{ instance.name }} {% if instance.overall_status == instance.PASSING_STATUS %}is back to normal{% else %}reporting {{ instance.overall_status }} status{% endif %}: {{ scheme }}://{{ host }}{% url instance pk=instance.id %}. {% if instance.overall_status != instance.PASSING_STATUS %}Checks failing:{% for check in instance.all_failing_checks %} {{ check.name }}{% if check.last_result.error %} ({{ check.last_result.error|safe }}){% endif %}{% endfor %}{% endif %}{% if alert %}{% for alias in users %} @{{ alias }}{% endfor %}{% endif %}"

sms_template = "Instance {{ instance.name }} {% if instance.overall_status == instance.PASSING_STATUS %}is back to normal{% else %}reporting {{ instance.overall_status }} status{% endif %}: {{ scheme }}://{{ host }}{% url instance pk=instance.id %}"

telephone_template = "This is an urgent message from Arachnys monitoring. Instance \"{{ instance.name }}\" is erroring. Please check Cabot urgently."


def send_alert(instance, duty_officers=None):
    users = instance.users_to_notify.all()
    if instance.email_alert:
        send_email_alert(instance, users, duty_officers)
    if instance.hipchat_alert:
        send_hipchat_alert(instance, users, duty_officers)
    if instance.sms_alert:
        send_sms_alert(instance, users, duty_officers)
    if instance.telephone_alert:
        send_telephone_alert(instance, users, duty_officers)


def send_email_alert(instance, users, duty_officers):
    emails = [u.email for u in users if u.email]
    if not emails:
        return
    c = Context({
        'instance': instance,
        'host': settings.WWW_HTTP_HOST,
        'scheme': settings.WWW_SCHEME
    })
    if instance.overall_status != instance.PASSING_STATUS:
        if instance.overall_status == instance.CRITICAL_STATUS:
            emails += [u.email for u in duty_officers]
        subject = '%s status for instance: %s' % (
            instance.overall_status, instance.name)
    else:
        subject = 'Instance back to normal: %s' % (instance.name,)
    t = Template(email_template)
    send_mail(
        subject=subject,
        message=t.render(c),
        from_email='Cabot <%s>' % settings.CABOT_FROM_EMAIL,
        recipient_list=emails,
    )


def send_hipchat_alert(instance, users, duty_officers):
    alert = True
    hipchat_aliases = [u.profile.hipchat_alias for u in users if hasattr(
        u, 'profile') and u.profile.hipchat_alias]
    if instance.overall_status == instance.WARNING_STATUS:
        alert = False  # Don't alert at all for WARNING
    if instance.overall_status == instance.ERROR_STATUS:
        if instance.old_overall_status in (instance.ERROR_STATUS, instance.ERROR_STATUS):
            alert = False  # Don't alert repeatedly for ERROR
    if instance.overall_status == instance.PASSING_STATUS:
        color = 'green'
        if instance.old_overall_status == instance.WARNING_STATUS:
            alert = False  # Don't alert for recovery from WARNING status
    else:
        color = 'red'
        if instance.overall_status == instance.CRITICAL_STATUS:
            hipchat_aliases += [u.profile.hipchat_alias for u in duty_officers if hasattr(
                u, 'profile') and u.profile.hipchat_alias]
    c = Context({
        'instance': instance,
        'users': hipchat_aliases,
        'host': settings.WWW_HTTP_HOST,
        'scheme': settings.WWW_SCHEME,
        'alert': alert,
    })
    message = Template(hipchat_template).render(c)
    _send_hipchat_alert(message, color=color, sender='Cabot/%s' % instance.name)


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


def send_sms_alert(instance, users, duty_officers):
    client = TwilioRestClient(
        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    mobiles = [u.profile.prefixed_mobile_number for u in users if hasattr(
        u, 'profile') and u.profile.mobile_number]
    if instance.is_critical:
        mobiles += [u.profile.prefixed_mobile_number for u in duty_officers if hasattr(
            u, 'profile') and u.profile.mobile_number]
    c = Context({
        'instance': instance,
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


def send_telephone_alert(instance, users, duty_officers):
    # No need to call to say things are resolved
    if instance.overall_status != instance.CRITICAL_STATUS:
        return
    client = TwilioRestClient(
        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    mobiles = [u.profile.prefixed_mobile_number for u in duty_officers if hasattr(
        u, 'profile') and u.profile.mobile_number]
    url = 'http://%s%s' % (settings.WWW_HTTP_HOST,
                           reverse('twiml-callback', kwargs={'instance_id': instance.id}))
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


def telephone_alert_twiml_callback(instance):
    c = Context({'instance': instance})
    t = Template(telephone_template).render(c)
    r = twiml.Response()
    r.say(t, voice='woman')
    r.hangup()
    return r
