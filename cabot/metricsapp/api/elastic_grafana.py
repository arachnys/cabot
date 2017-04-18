import logging
import json
from elasticsearch_dsl import Search, A
from elasticsearch_dsl.query import Range
from django.core.exceptions import ValidationError
from cabot.metricsapp.defs import ES_SUPPORTED_METRICS, ES_TIME_RANGE, ES_DEFAULT_INTERVAL


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
        terms_settings['order'] = {order_by: settings['order']}

    # size 0 in Grafana is equivalent to no size setting in an Elasticsearch query
    size = int(settings.get('size') or 0)
    if size and int(size) > 0:
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
    search = Search().query('query_string', query=series['query'], analyze_wildcard=True) \
        .query(Range(** {series['timeField']: {'gte': min_time}}))
    _add_aggs(search.aggs, series, min_time, default_interval)
    return search.to_dict()


def template_response(data, templating_dict):
    """
    Change the panel info from the Grafana dashboard API response
    based on the dashboard templates
    :param data: any string portion of the response from the Grafana API
    :param templating_info: dictionary of {template_name, output_value}
    :return: panel_info with all templating values filled in
    """
    data = json.dumps(data)
    # Loop through all the templates and replace them if they're used in this panel
    for name, value in templating_dict.iteritems():
        data = data.replace('${}'.format(name), value)
    return json.loads(data)


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
