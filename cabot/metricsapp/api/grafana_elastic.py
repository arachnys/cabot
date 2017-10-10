import logging
from collections import defaultdict
from elasticsearch_dsl import Search, A
from elasticsearch_dsl.query import Range
from django.core.exceptions import ValidationError
from pytimeparse import parse
from cabot.metricsapp import defs
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

    min_doc_count = settings.get('min_doc_count')
    if min_doc_count:
        terms_settings['min_doc_count'] = int(min_doc_count)

    order_by = settings.get('orderBy')
    if order_by:
        terms_settings['order'] = {order_by: settings['order']}

    # size 0 in Grafana is equivalent represents "unlimited size," which actually
    # means Grafana sets the size to 500 in their query.
    size = settings.get('size')
    if size:
        size = int(size)
        if size == 0:
            terms_settings['size'] = defs.ES_MAX_TERMS_SIZE
        else:
            terms_settings['size'] = size

    return terms_settings


def _get_filters_settings(agg):
    """
    Get the settings for a filters aggregation
    :param agg: the filter aggregation json data
    :return: dict of {setting_name: setting_value}
    """
    filter_settings = dict(filters=dict())

    settings = agg['settings']

    filters = settings['filters']

    for _filter in filters:
        query_string = {"query_string": {"query": _filter['query'], "analyze_wildcard": True}}
        filter_settings["filters"][_filter['query']] = query_string

    return filter_settings


def _get_histogram_settings(agg):
    """
    Get the settings for a histogram aggregation
    :param agg: the histogram aggregation json data
    :return: dict of {setting_name: setting_value}
    """
    histogram_settings = dict(field=agg['field'])

    settings = agg['settings']

    histogram_settings['interval'] = settings.get('interval')

    min_doc_count = settings.get('min_doc_count')
    if min_doc_count:
        histogram_settings['min_doc_count'] = int(min_doc_count)

    return histogram_settings


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


def _get_metric_name(series, metric_type, metric):
    """
    Get the name for a metric (including hidden values, aliases, etc) from a series
    :param series: a "target" in the Grafana dashboard API response
    :param metric_type: the type of metric (sum, avg, etc.)
    :param metric: one value in the 'metric' section of the series
    :return: the metric name
    """
    alias = series.get('alias')
    # Ignore templated aliases because they will be the same thing for every series
    if alias is not None and not alias.startswith('{{') and alias != "":
        metric_name = '{}{}{}'.format(metric_type, defs.ALIAS_DELIMITER, alias)
    else:
        metric_name = metric_type

    if metric.get('hide') is True:
        metric_name = '{}_{}'.format(metric_name, defs.HIDDEN_METRIC_SUFFIX)

    return metric_name


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
            # If ordering by a sub-aggregation, add the sub-aggregation as an aggregation on the current nesting level.
            # We know that we are ordering by a sub-aggregation when the value of orderBy is a number. This number is
            # the id of the metric representing the sub-aggregation which we need to add.
            order_by = agg['settings'].get('orderBy')
            if order_by and order_by.isdigit():
                metric = next(m for m in series['metrics'] if m['id'] == order_by)
                settings = {'field': metric['field']}
                search_aggs.bucket(metric['id'], A({metric['type']: settings}))

        # Filter functionality can be accomplished with multiple queries instead
        elif agg_type == 'filters':
            settings = _get_filters_settings(agg)
            search_aggs = search_aggs.bucket('agg', A({'filters': settings}))

        elif agg_type == 'histogram':
            settings = _get_histogram_settings(agg)
            search_aggs = search_aggs.bucket('agg', A({'histogram': settings}))

        # Geo hash grid doesn't make much sense for alerting
        else:
            raise ValidationError('{} aggregation not supported.'.format(agg_type))

    if not date_histogram:
        raise ValidationError('Dashboard must include a date histogram aggregation.')

    settings = _get_date_histogram_settings(date_histogram, min_time, default_interval)
    search_aggs = search_aggs.bucket('agg', A({'date_histogram': settings}))

    pipeline_id_name_mapping = dict()
    pipeline_metrics = []
    for metric in series['metrics']:
        metric_type = metric['type']
        metric_name = _get_metric_name(series, metric_type, metric)

        # Special case for count--not actually an elasticsearch metric, but supported
        if metric_type not in defs.ES_SUPPORTED_METRICS.union(set(['count'])):
            raise ValidationError('Metric type {} not supported.'.format(metric_type))

        # Store the mapping of "id" to "name" to use for pipeline mappings
        pipeline_id_name_mapping[metric['id']] = metric_name

        # Handle pipeline aggs at the end (the field 'pipelineAgg' will refer to the id
        # of another metric
        pipeline_agg = metric.get('pipelineAgg')
        if pipeline_agg is not None and pipeline_agg.isdigit():
            pipeline_metrics.append(metric)
            continue

        # value_count the time field if count is the metric (since the time field must always be present)
        if metric_type == 'count':
            search_aggs.metric('value_{}'.format(metric_name), 'value_count', field=series['timeField'])

        # percentiles has an extra setting for percents
        elif metric_type == 'percentiles':
            search_aggs.metric(metric_name, 'percentiles', field=metric['field'],
                               percents=metric['settings']['percents'])

        else:
            search_aggs.metric(metric_name, metric_type, field=metric['field'])

    for metric in pipeline_metrics:
        pipeline_agg = metric['pipelineAgg']
        metric_type = metric_name = metric['type']
        if metric.get('hide') is True:
            metric_name = '{}_{}'.format(metric_name, defs.HIDDEN_METRIC_SUFFIX)

        bucket = pipeline_id_name_mapping.get(pipeline_agg)
        if bucket is None:
            raise ValidationError('Cannot find metric with id {} for pipeline metric'.format(pipeline_agg))

        search_aggs.pipeline(metric_name, metric_type, buckets_path=bucket)


def build_query(series, min_time=defs.ES_TIME_RANGE, default_interval=defs.ES_DEFAULT_INTERVAL):
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

        # All means all the options
        # Multi-valued templates are surrounded by parentheses and combined with OR
        if '$__all' in template_value:
            options = [option['value'] for option in template['options']]
            # If there aren't any options, fall back to selecting everything
            if options == []:
                templates[template_name] = '*'
            else:
                templates[template_name] = '({})'.format(' OR '.join(options))

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
    time_from = panel_info.get('timeFrom')
    if time_from is not None:
        # Format of timeFrom is '2h', '1m', etc.
        min_time = 'now-{}'.format(time_from)
    else:
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

        _adjust_extended_bounds(query['aggs'], minimum)

    return queries


def _adjust_extended_bounds(aggs, minimum):
    """
    Adjust extended bounds so we don't fetch more data than we need to
    :param aggs: Takes in the 'aggs' part of a query
    :param minimum: the time range to limit extended_bounds to - formatted as '{}m'.format(time_range)
    :return: None
    """
    next_level = aggs.get('agg')

    if not next_level or len(next_level) < 2:
        return

    for k, v in next_level.iteritems():
        if k == 'date_histogram':
            v['extended_bounds']['min'] = 'now-{}'.format(minimum)
            v['extended_bounds']['max'] = 'now'
        return _adjust_extended_bounds(next_level['aggs'], minimum)
