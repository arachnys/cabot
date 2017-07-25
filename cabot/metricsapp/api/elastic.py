from django.conf import settings
from django.core.exceptions import ValidationError
from elasticsearch import Elasticsearch
from cabot.metricsapp import defs


def _find_base_metric_name(name):
    """
    Remove extra info we've added to a metric name and return just sum, avg, etc.
    :param name: Metric name in the response from Elasticsearch
    :return: shortened metric name that should be the same as the metric type
    """
    # If the metric is hidden ignore the hidden suffix
    metric = name.replace('_{}'.format(defs.HIDDEN_METRIC_SUFFIX), '')
    # Get rid of a possible alias name
    return metric.split(defs.ALIAS_DELIMITER)[0]


def create_es_client(urls, timeout=settings.ELASTICSEARCH_TIMEOUT):
    """
    Create an elasticsearch-py client
    :param urls: comma-separated string of urls
    :param timeout: timeout for queries to the client
    :return: a new elasticsearch-py client
    """
    urls = [url.strip() for url in urls.split(',')]
    return Elasticsearch(urls, timeout=timeout)


def validate_query(query, msg_prefix=defs.ES_VALIDATION_MSG_PREFIX):
    """
    Validate that an Elasticsearch query is in the format we want
    (all aggregations named 'agg', 'date_histogram' most internal
    aggregation, other metrics named the same thing as their metric
    type, e.g. max, min, avg...).
    :param query: the raw Elasticsearch query
    """
    # Loop through all the aggregations, stopping when we hit a date_histogram
    query = query.get('aggs')
    if query is None:
        raise ValidationError('{}: query must at least include a date_histogram aggregation.'.format(msg_prefix))

    query = query.get('agg')
    if query is None:
        raise ValidationError('{}: aggregations should be named "agg."'.format(msg_prefix))

    if 'date_histogram' not in query:
        validate_query(query)
        return

    # date_histogram must be the innermost aggregation
    if 'agg' in query:
        raise ValidationError('{}: date_histogram must be the innermost aggregation (besides metrics).'
                              .format(msg_prefix))

    # The rest of the aggs should be metrics
    query = query.get('aggs')
    if query is None:
        raise ValidationError('{}: query must include a metric'.format(msg_prefix))

    for metric, items in query.iteritems():
        metric = _find_base_metric_name(metric)

        if metric not in defs.ES_SUPPORTED_METRICS:
            raise ValidationError('{}: unsupported metric "{}."'.format(msg_prefix, metric))

        if metric not in items:
            raise ValidationError('{}: metric name must be the same as the metric type.'.format(msg_prefix))
