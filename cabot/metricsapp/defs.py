# Constant definitions
ES_SUPPORTED_METRICS = set(['min', 'max', 'avg', 'value_count', 'sum', 'cardinality', 'moving_avg',
                            'derivative', 'percentiles'])

ES_VALIDATION_MSG_PREFIX = 'Elasticsearch query format error'

ES_TIME_RANGE = 'now-10m'

ES_DEFAULT_INTERVAL = '1m'

GRAFANA_SYNC_TIMEDELTA_MINUTES = 30
