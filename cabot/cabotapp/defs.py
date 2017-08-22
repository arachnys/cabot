# Constant definitions

CHECK_TYPES = (
    ('>', 'Greater than'),
    ('>=', 'Greater than or equal'),
    ('<', 'Less than'),
    ('<=', 'Less than or equal'),
    ('==', 'Equal to'),
)

RAW_DATA_LIMIT = 500000                     # noqa

DEFAULT_CHECK_FREQUENCY = 5                 # noqa
DEFAULT_CHECK_RETRIES   = 0                 # noqa

DEFAULT_GRAPHITE_EXPECTED_NUM_HOSTS   = 0   # noqa
DEFAULT_GRAPHITE_EXPECTED_NUM_METRICS = 0   # noqa
DEFAULT_GRAPHITE_INTERVAL             = 5   # noqa

DEFAULT_HTTP_TIMEOUT     = 30               # noqa
MAX_HTTP_TIMEOUT         = 32               # noqa
DEFAULT_HTTP_STATUS_CODE = 200              # noqa

DEFAULT_TCP_TIMEOUT = 8                     # noqa
MAX_TCP_TIMEOUT     = 16                    # noqa

