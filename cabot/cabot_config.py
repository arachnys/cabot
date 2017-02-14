import os

GRAPHITE_API = os.environ.get('GRAPHITE_API')
GRAPHITE_USER = os.environ.get('GRAPHITE_USER')
GRAPHITE_PASS = os.environ.get('GRAPHITE_PASS')
GRAPHITE_FROM = os.getenv('GRAPHITE_FROM', '-10minute')
JENKINS_API = os.environ.get('JENKINS_API')
JENKINS_USER = os.environ.get('JENKINS_USER')
JENKINS_PASS = os.environ.get('JENKINS_PASS')
CALENDAR_ICAL_URL = os.environ.get('CALENDAR_ICAL_URL')
WWW_HTTP_HOST = os.environ.get('WWW_HTTP_HOST')
WWW_SCHEME = os.environ.get('WWW_SCHEME', "https")
ALERT_INTERVAL = int(os.environ.get('ALERT_INTERVAL', 10))
NOTIFICATION_INTERVAL = int(os.environ.get('NOTIFICATION_INTERVAL', 120))
INFLUXDB_DSN = os.environ.get('INFLUXDB_DSN')
INFLUXDB_TIMEOUT = int(os.environ.get('INFLUXDB_TIMEOUT', 30))
INFLUXDB_VERSION = os.environ.get('INFLUXDB_VERSION', '0.8')
INFLUXDB_FROM = int(os.environ.get('INFLUXDB_FROM', '60'))
INFLUXDB_LIMIT = int(os.environ.get('INFLUXDB_LIMIT', '100'))

# While displaying a list of available metrics, cabot will fetch the
# actual metrics values only if the metrics list is lesser than this number
METRIC_FETCH_LIMIT = int(os.environ.get('METRIC_FETCH_LIMIT', '20'))

# Default plugins are used if the user has not specified.
CABOT_PLUGINS_ENABLED = os.environ.get('CABOT_PLUGINS_ENABLED',
    ','.join(['cabot_alert_hipchat',
              'cabot_alert_twilio',
              'cabot_alert_email',
              'cabot_alert_pagerduty'
    ]))
