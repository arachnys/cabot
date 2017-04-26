import datetime
from django.conf import settings
from django.utils.timezone import now, get_current_timezone
from dateutil import rrule
from icalendar import Calendar
import requests

import logging
logger = logging.getLogger(__name__)


MAX_FUTURE = 60  # days


def ensure_tzaware(dt):
    if dt.tzinfo is None:
        return get_current_timezone().localize(dt)
    return dt


def _recurring_component_to_events(component):
    """
    Given an icalendar component with an "RRULE"
    Return a list of events as dictionaries
    """
    rrule_as_str = component.get('rrule').to_ical()
    recur_rule = rrule.rrulestr(rrule_as_str,
                                dtstart=ensure_tzaware(component.decoded('dtstart')))
    recur_set = rrule.rruleset()
    recur_set.rrule(recur_rule)
    if 'exdate' in component:
        lines = component.decoded('exdate')
        if not hasattr(lines, '__iter__'):
            lines = [lines]
        for exdate_line in lines:
            for exdate in exdate_line.dts:
                recur_set.exdate(ensure_tzaware(exdate.dt))

    # get list of events in MAX_FUTURE days
    utcnow = now()
    later = utcnow + datetime.timedelta(days=MAX_FUTURE)
    start_times = recur_set.between(utcnow, later)

    # build list of events
    event_length = component.decoded('dtend') - component.decoded('dtstart')
    events = []
    for start in start_times:
        events.append({
            'start': start,
            'end': start + event_length,
            'summary': component.decoded('summary'),
            'uid': component.decoded('uid'),
            'last_modified': component.decoded('last-modified'),
        })
    return events


def get_calendar_data():
    feed_url = settings.CALENDAR_ICAL_URL
    resp = requests.get(feed_url)
    cal = Calendar.from_ical(resp.content)
    return cal


def get_events():
    events = []
    for component in get_calendar_data().walk():
        if component.name == 'VEVENT':
            if 'rrule' in component:
                events.extend(_recurring_component_to_events(component))
            else:
                try:
                    events.append({
                        'start': component.decoded('dtstart'),
                        'end': component.decoded('dtend'),
                        'summary': component.decoded('summary'),
                        'uid': component.decoded('uid'),
                        'last_modified': component.decoded('last-modified'),
                    })
                except KeyError:
                    logger.debug('Failed to parse VEVENT component: %s',
                                 component.get('uid', 'no uid available'))
    return events
