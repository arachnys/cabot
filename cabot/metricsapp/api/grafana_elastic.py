import logging
from collections import defaultdict
from elasticsearch_dsl import Search, A
from elasticsearch_dsl.query import Range
from django.core.exceptions import ValidationError
from pytimeparse import parse
from cabot.metricsapp.defs import ES_SUPPORTED_METRICS, ES_TIME_RANGE, ES_DEFAULT_INTERVAL
from .grafana import template_response


logger = logging.getLogger(__name__)


def _get_terms_settings(agg):
    """
    Get the settings for a terms aggregation.
    :param agg: the terms aggregation json data
    :return: dict of {setting_name: setting_value}
    """
    terms_settings = dict(field=agg['field'])

    settings = agg['settings']
    order_by = settings.get('orderBy')
    if order_by:
        # Grafana indicates sub-aggregation ordering by a number representing the aggregation
        if order_by.isdigit():
            raise ValidationError('Ordering by sub-aggregations not supported.')

        terms_settings['order'] = {order_by: settings['order']}

    # size 0 in Grafana is equivalent to no size setting in an Elasticsearch query
    size = int(settings.get('size') or 0)
    if size and size > 0:
        terms_settings['size'] = int(size)

    min_doc_count = settings.get('min_doc_count')
    if min_doc_count:
        terms_settings['min_doc_count'] = int(min_doc_count)

    return terms_settings


def _get_date_histogram_settings(agg, min_time, default_interval):
    """
    Get the settings for a date_histogram aggregation.
    :param agg: the date_histogram aggregation json data
    :param min_time: the earliest time we're looking for
    :param default_interval: default for the group by interval
    :return: dict of {setting_name: setting_value}
    """
    interval = agg['settings']['interval']
    if interval == 'auto':
        interval = default_interval

    return dict(field=agg['field'], interval=interval, extended_bounds={'min': min_time, 'max': 'now'})


def _add_aggs(search_aggs, series, min_time, default_interval):
    """
    Add the ES aggregations from the input Grafana API series info to an input search
    :param search_aggs: Search().aggs
    :param series: a "target" in the Grafana dashboard API response
    :param min_time: the earliest time we're looking for
    :param default_interval: default for the group by interval
    :return None
    """
    date_histogram = None

    for agg in series['bucketAggs']:
        # date_histogram must be the final aggregation--save it to add after the other aggregations
        agg_type = agg['type']
        if agg_type == 'date_histogram':
            date_histogram = agg
            continue

        # Add extra settings for "terms" aggregation
        elif agg_type == 'terms':
            settings = _get_terms_settings(agg)
            search_aggs = search_aggs.bucket('agg', A({'terms': settings}))

        # Filter functionality can be accomplished with multiple queries instead
        elif agg_type == 'filter':
            raise ValidationError('Filter aggregation not supported. Please change the query instead.')

        # Geo hash grid doesn't make much sense for alerting
        else:
            raise ValidationError('{} aggregation not supported.'.format(type))

    if not date_histogram:
        raise ValidationError('Dashboard must include a date histogram aggregation.')

    settings = _get_date_histogram_settings(date_histogram, min_time, default_interval)
    search_aggs = search_aggs.bucket('agg', A({'date_histogram': settings}))

    for metric in series['metrics']:
        metric_type = metric['type']

        # Special case for count--not actually an elasticsearch metric, but supported
        if metric_type not in ES_SUPPORTED_METRICS.union(set(['count'])):
            raise ValidationError('Metric type {} not supported.'.format(metric_type))

        # value_count the time field if count is the metric (since the time field must always be present)
        if metric_type == 'count':
            search_aggs.metric('value_count', 'value_count', field=series['timeField'])

        # percentiles has an extra setting for percents
        elif metric_type == 'percentiles':
            search_aggs.metric('percentiles', 'percentiles', field=metric['field'],
                               percents=metric['settings']['percents'])

        else:
            search_aggs.metric(metric['type'], metric['type'], field=metric['field'])


def build_query(series, min_time=ES_TIME_RANGE, default_interval=ES_DEFAULT_INTERVAL):
    """
    Given series information from the Grafana API, build an Elasticsearch query
    :param series: a "target" in the Grafana dashboard API response
    :param min_time: the earliest time we're looking for
    :param default_interval: default for the group by interval
    :return: Elasticsearch json query
    """
    query = series.get('query')
    # If there's no specified query, query for everything
    if query is None:
        query = '*'

    search = Search().query('query_string', query=query, analyze_wildcard=True) \
        .query(Range(** {series['timeField']: {'gte': min_time}}))
    _add_aggs(search.aggs, series, min_time, default_interval)
    return search.to_dict()


def create_elasticsearch_templating_dict(dashboard_info):
    """
    Make a dictionary of {template_name: template_value} based on
    the templating section of the Grafana dashboard API response. Change the values
    so that they're in the correct Elasticsearch syntax.
    :param dashboard_info: info from the Grafana dashboard API
    :return: dict of {template_name: template_value} for all templates for this
    dashboard
    """
    templates = {}
    templating_info = dashboard_info['dashboard']['templating']

    # Not all data in the templating section are templates--filter out the ones without current values
    for template in filter(lambda template: template.get('current'), templating_info['list']):
        template_value = template['current']['value']
        template_name = template['name']

        # Template for all values should be "*" in the query
        if '$__all' in template_value:
            templates[template_name] = '*'

        # Multi-valued templates are surrounded by parentheses and combined with OR
        elif isinstance(template_value, list):
            templates[template_name] = '({})'.format(' OR '.join(template_value))

        # Interval can also be automatically set
        elif template_value == '$__auto_interval':
            templates[template_name] = 'auto'

        else:
            templates[template_name] = template_value

    return templates


def get_es_status_check_fields(dashboard_info, panel_info, series_list):
    """
    Get the fields necessary to create an ElasticsearchStatusCheck (that aren't in a generic
    MetricsStatusCheck).
    :param dashboard_info: all info for a dashboard from the Grafana API
    :param panel_info: info about the panel we're alerting off of from the Grafana API
    :param series_list: the series the user selected to use
    :return dictionary of the required ElasticsearchStatusCheck fields (queries)
    """
    fields = defaultdict(list)

    templating_dict = create_elasticsearch_templating_dict(dashboard_info)
    series_list = [s for s in panel_info['targets'] if s['refId'] in series_list]
    min_time = dashboard_info['dashboard']['time']['from']
    default_interval = panel_info.get('interval')

    if default_interval is not None:
        # interval can be in format (>1h, <10m, etc.). Get rid of symbols
        templated_interval = str(template_response(default_interval, templating_dict))
        default_interval = filter(str.isalnum, templated_interval)

    for series in series_list:
        templated_series = template_response(series, templating_dict)
        if default_interval is not None and default_interval != 'auto':
            query = build_query(templated_series, min_time=min_time, default_interval=default_interval)
        else:
            query = build_query(templated_series, min_time=min_time)

        fields['queries'].append(query)

    return fields


def adjust_time_range(queries, time_range):
    """
    Adjust the range setting of a list of queries to a new minimum value (so
    we're not fetching a ton of unused data)
    :param queries: list of ES json queries
    :param time_range: time range for the status check
    :return: the new query
    """
    minimum = '{}m'.format(time_range)

    for n, query in enumerate(queries):
        # Find the minimum range value and set it
        for m, subquery in enumerate(query['query']['bool']['must']):
            range = subquery.get('range')
            if range is not None:
                # There should only be one value in range
                for value in range:
                    time_field = value
                curr_minimum = range[time_field]['gte']
                if parse(minimum) != parse(curr_minimum):
                    query['query']['bool']['must'][m]['range'][time_field]['gte'] = 'now-{}'.format(minimum)
                    queries[n] = query

    return queries