
from django.conf import settings
from icalendar import Calendar, Event
import requests


def get_calendar_data():
    feed_url = settings.CALENDAR_ICAL_URL
    resp = requests.get(feed_url)
    cal = Calendar.from_ical(resp.content)
    return cal


def get_events():
    events = []
    for component in get_calendar_data().walk():
        if component.name == 'VEVENT':
            events.append({
                'start': component.decoded('dtstart'),
                'end': component.decoded('dtend'),
                'summary': component.decoded('summary'),
                'uid': component.decoded('uid'),
            })
    return events
