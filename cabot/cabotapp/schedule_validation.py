from django.utils import timezone
from django.utils.timezone import make_naive

import models


def _find_gaps(schedule, starting_from=None):
    """
    Returns a list of "gaps" in a schedule where no one is on call.
    If no one is on call between now and the first item on the calendar,
    :param schedule: Schedule model object (that has already had update_shifts() called on it)
    :param starting_from: time to start checking for gaps; if starting_from is before the earliest shift,
                          it is considered a gap (since no one is on call)
    :return: a list of (start, end) tuples when no one is scheduled
    """
    gaps = []

    current = starting_from if starting_from else timezone.now()
    for shift in models.Shift.objects.filter(schedule=schedule).order_by('start', 'end'):
        if shift.start > current:
            gaps.append((current, shift.start))
        if shift.end > current:
            current = shift.end

    return gaps


def _delta_to_str(delta):
    """
    Pretty-print timedelta for emails
    :param delta: a timedelta object
    """
    seconds = abs(int(delta.total_seconds()))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if days > 0:
        parts.append('%dd' % days)
    if hours > 0:
        parts.append('%dh' % hours)
    if minutes > 0:
        parts.append('%dm' % minutes)
    if seconds > 0:
        parts.append('%ds' % seconds)

    return ', '.join(parts)


def _find_problems(schedule, current_time=None):
    """
    Returns a list of configuration problems with a schedule. Returns an empty list if the schedule is good.
    Checks include:
    * Is there a fallback officer? Do they have an email set?
    * Is the schedule empty?
    * Are there any gaps between the events in the schedule (where no one is on call)?
    :param schedule: schedule to check (should already be updated from update_shifts())
    :param current_time: time to start checking the schedule from (to see if anyone is currently on call),
                         None for now
    :return: list of strings describing any problems in the schedule ("problems")
    """
    problems = []

    if not schedule.fallback_officer:
        problems.append("The schedule has no fallback officer.")
    elif not schedule.fallback_officer.email:
        problems.append("The fallback officer does not have an email set.")

    any_shifts = (models.Shift.objects.filter(schedule=schedule).count() > 0)
    if not any_shifts:
        problems.append("The schedule is empty, so no one is on call.")

    gaps = _find_gaps(schedule, starting_from=current_time)
    if len(gaps) > 0:
        # only print the first 5 gaps
        max_reported_gaps = 5

        # convert to naive timezones to avoid printing +00:00 with each time (which is noisy)
        tz = timezone.get_current_timezone()

        # this gives something like 'UTC', 'EST', 'PST', etc
        # timezone name can change depending on what specific time we're talking about (due to daylight savings, etc...)
        # since we don't want to include the timezone info with every timestamp, we just use the time of the first gap
        # also note this method requires using pytz as the timezone backend (which we do)
        tzname = tz.tzname(gaps[0][0], is_dst=False)

        gap_strs = ['* {} to {} ({})'.format(make_naive(gap[0], tz), make_naive(gap[1], tz),
                                             _delta_to_str(gap[1] - gap[0]))
                    for gap in gaps[:max_reported_gaps]]
        problems.append("There are gaps in the schedule (times are {}):\n{}".format(tzname, '\n'.join(gap_strs)))

        if len(gaps) > max_reported_gaps:
            problems[-1] += "\n(Plus another {} gap(s) not listed here.)".format(len(gaps) - max_reported_gaps)

    return problems


def update_schedule_problems(schedule, now=None):
    problems_list = _find_problems(schedule, now)

    if len(problems_list) == 0:
        models.ScheduleProblems.objects.filter(schedule=schedule).delete()
        return

    problems_model = models.ScheduleProblems.objects.get_or_create(schedule=schedule)[0]

    # we have some problems - update the saved problem list
    problems_str = '\n\n'.join(problems_list)
    problems_model.text = problems_str
    problems_model.save()
