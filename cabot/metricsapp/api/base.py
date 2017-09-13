from celery.utils.log import get_task_logger
import json
import time
from cabot.cabotapp.models import Service, StatusCheckResult


logger = get_task_logger(__name__)


def _get_error_message(check, metric_name, value, check_value):
    return u'{}: {:0.1f} {} {:0.1f}'.format(metric_name, value, check.check_type, check_value)


def _point_failure_check(check_type, check_value, value):
    """
    Check whether a point fails the check.
    :param check_type: the type of status check (<, >, etc.)
    :param check_value: the failure value
    :param value: the value we're checking success/failure for
    :return: True if the check fails, False if it succeeds
    """
    if check_type == '<':
        return not value < check_value
    elif check_type == '<=':
        return not value <= check_value
    elif check_type == '>':
        return not value > check_value
    elif check_type == '>=':
        return not value >= check_value
    elif check_type == '==':
        return not value == check_value
    else:
        raise ValueError(u'Check type {} not supported'.format(check_type))


def _add_threshold_data(check, series):
    """
    Add threshold values to a raw data series
    :param check: the status check
    :param series: the data series
    :return: the data series with high alert/warning thresholds
    """
    first_series_data = series.get('data')[0].get('datapoints')
    if first_series_data:
        start_time, _ = first_series_data[0]
        end_time, _ = first_series_data[-1]

        # Add threshold line(s) for the graph
        if check.warning_value is not None:
            warning_threshold = dict(series='alert.warning_threshold',
                                     datapoints=[[start_time, check.warning_value],
                                                 [end_time, check.warning_value]])
            series['data'].append(warning_threshold)

        if check.high_alert_value is not None:
            high_alert_threshold = dict(series='alert.high_alert_threshold',
                                        datapoints=[[start_time, check.high_alert_value],
                                                    [end_time, check.high_alert_value]])
            series['data'].append(high_alert_threshold)

    try:
        return json.dumps(series['data'], indent=2)
    except TypeError:
        logger.exception('Error when serializing series to json. Series: {}'.format(series))
        return series['data']


def run_metrics_check(check):
    """
    Run the status check.
    :param check: the status check
    :return: a StatusCheckResult containing success/failure/error information
    """
    result = StatusCheckResult(check=check)
    # result.succeeded will be set to False when failures happen
    result.succeeded = True

    series = check.get_series()

    if series['error'] is True:
        result.succeeded = False
        message = series.get('error_message')
        result.error = 'Error fetching metric from source: {}'.format(message)
        logger.exception('Error fetching metrics: {}: {}'.format(series.get('error_code'), message))
        return result

    # Oldest point we'll look at (time range is in seconds)
    earliest_point = time.time() - check.time_range * 60

    parsed_series = series['data']
    logger.info('Processing series {}'.format(str(parsed_series)))
    for series_data in parsed_series:
        for point in series_data['datapoints']:
            timestamp, value = point

            # Ignore data outside the time frame
            if timestamp <= earliest_point:
                logger.debug('Point {} is older than reference timestamp {}'.format(
                    str(point), str(earliest_point)
                ))
                continue

            # If there's a failure for high alert, the check fails
            if check.high_alert_value is not None and _point_failure_check(check.check_type,
                                                                           check.high_alert_value,
                                                                           value):
                # Set the importance so the check fails at the right level
                check.importance = check.high_alert_importance
                result.succeeded = False
                result.error = _get_error_message(check, series_data['series'], value, check.high_alert_value)
                result.raw_data = _add_threshold_data(check, series)
                return result

            # If there's a failure for low alert, keep looping in case another point is failing
            # at the high alert level. Don't check for a warning if we've already found one
            # (result.succeeded == False)
            if result.succeeded and check.warning_value is not None and \
                    _point_failure_check(check.check_type, check.warning_value, value):
                # Set the importance so the check fails at the right level
                check.importance = Service.WARNING_STATUS
                result.succeeded = False
                result.error = _get_error_message(check, series_data['series'], value, check.warning_value)

        logger.info('Finished processing series {}'.format(series_data['series']))

    result.raw_data = _add_threshold_data(check, series)
    return result
