import influxdb.influxdb08
import logging

from django.conf import settings
from collections import defaultdict


# Keep a globally configured client ready
_influxdb_client = None


def _get_influxdb_client(influxdb_dsn=settings.INFLUXDB_DSN,
                         timeout=settings.INFLUXDB_TIMEOUT,
                         version=settings.INFLUXDB_VERSION):

    # Keep a globally configured client ready
    global _influxdb_client

    if version == '0.8':
        client_kls = influxdb.influxdb08.InfluxDBClient
    else:
        raise ValueError('InfluxDB version %s is unsupported' % version)

    if _influxdb_client is None:
        _influxdb_client = client_kls.from_DSN(influxdb_dsn, timeout=timeout)

    return _influxdb_client


def get_data(pattern, selector='value',
             where_clause=None,
             group_by=None,
             fill_empty=None,
             time_delta=settings.INFLUXDB_FROM,
             limit=settings.INFLUXDB_LIMIT,
             fetchall=False):
    '''
    Query a metric and it's data from influxdb.
    Return the value in a graphite compatible format

    * selector - can be specified as
                 'value'
                 'mean(value)'
                 'percentile(value, 95)'

    * group_by - can be specified as
                 'time(10s)'
                 'time(60m), host'

    * fill_empty - can be Null, or an integer value
    '''

    if fill_empty is not None:
        fill_str = 'fill(%d)' % fill_empty
    else:
        fill_str = ''

    if group_by is None:
        group_by = ''

    if group_by:
        group_by = 'group by %s' % group_by
    else:
        # Fill is allowed only with a 'group by' clause
        fill_str = ''

    if where_clause:
        where_str = 'where %s' % where_clause
    else:
        where_str = ''

    # Prepare a time limit for the the query
    if time_delta is not None:
        time_str = 'time > now() - %dm' % (time_delta)

        if where_str:
            where_str += ' and %s' % time_str
        else:
            where_str = 'where %s' % time_str

    if limit is not None:
        limit_str = 'limit %d' % (limit)
    else:
        limit_str = ''

    if fetchall:
        pattern = '.*%s.*' % (pattern)

    data = defaultdict(list)
    query = 'select %s from /%s/ %s %s %s %s order asc' % \
        (selector, pattern, group_by, fill_str, where_str, limit_str)


    logging.debug('Make influxdb query %s' % query)

    client = _get_influxdb_client()
    resp = client.query(query, chunked=True)

    # Convert the result into a graphite compatible output
    # This is a hack to get influxdb working well with cabot
    for series in resp:
        name = series['name']

        if len(series['columns']) == 2:
            for ts, value in series['points']:
                data[name].append((value, ts))
        elif series['columns'][2] == 'value':
            for ts, seq, value in series['points']:
                data[name].append((value, ts))
        else:
            for ts, value, group in series['points']:
                data['%s.%s' % (name, group)].append((value, ts))

    return [dict(target=key, datapoints=value)
            for key, value in data.iteritems()]


def get_matching_metrics(pattern):
    '''
    Given a pattern, find all matching metrics for it
    '''
    query = 'list series /.*%s.*/' % (pattern)
    logging.debug('Make influxdb query %s' % query)

    client = _get_influxdb_client()
    resp = client.query(query, chunked=True)
    metrics = []

    for point in resp[0]['points']:
        series = point[1]
        metrics.append(dict(is_leaf=1, name=series, path=series))

    return dict(metrics=metrics)


def get_all_metrics(limit=None):
    '''
    Grabs all metrics by navigating find API recursively
    '''
    metrics = []

    def get_leafs_of_node(nodepath):
        for obj in get_matching_metrics(nodepath, limit)['metrics']:
            if int(obj['is_leaf']) == 1:
                metrics.append(obj['path'])
            else:
                get_leafs_of_node(obj['path'])
    get_leafs_of_node('')
    return metrics


def parse_metric(metric,
                 selector='value',
                 group_by=None,
                 fill_empty=None,
                 where_clause=None,
                 time_delta=settings.INFLUXDB_FROM):
    '''
    Returns dict with:
    - num_series_with_data: Number of series with data
    - num_series_no_data: Number of total series
    - max
    - min
    - average_value
    '''
    ret = {
        'num_series_with_data': 0,
        'num_series_no_data': 0,
        'error': None,
        'all_values': [],
        'raw': ''
    }
    try:
        data = get_data(metric,
                        selector=selector,
                        group_by=group_by,
                        fill_empty=fill_empty,
                        where_clause=where_clause,
                        time_delta=time_delta,
                        limit=None)

    except Exception, exp:
        ret['error'] = 'Error getting data from InfluxDB: %s' % exp
        ret['raw'] = ret['error']
        logging.exception('Error getting data from InfluxDB: %s' % exp)
        return ret

    all_values = []
    for target in data:
        values = [float(t[0])
                  for t in target['datapoints'][-time_delta:]
                  if t[0] is not None]
        if values:
            ret['num_series_with_data'] += 1
        else:
            ret['num_series_no_data'] += 1
        all_values.extend(values)
    if all_values:
        ret['max'] = max(all_values)
        ret['min'] = min(all_values)
        ret['average_value'] = sum(all_values) / len(all_values)
    ret['all_values'] = all_values
    ret['raw'] = data

    return ret
