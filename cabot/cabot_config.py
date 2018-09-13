import os

JENKINS_API = os.environ.get('JENKINS_API')
JENKINS_USER = os.environ.get('JENKINS_USER')
JENKINS_PASS = os.environ.get('JENKINS_PASS')
CALENDAR_ICAL_URL = os.environ.get('CALENDAR_ICAL_URL')
WWW_HTTP_HOST = os.environ.get('WWW_HTTP_HOST')
WWW_SCHEME = os.environ.get('WWW_SCHEME', "https")
ALERT_INTERVAL = int(os.environ.get('ALERT_INTERVAL', 10))
NOTIFICATION_INTERVAL = int(os.environ.get('NOTIFICATION_INTERVAL', 120))

# While displaying a list of available metrics, cabot will fetch the
# actual metrics values only if the metrics list is lesser than this number
METRIC_FETCH_LIMIT = int(os.environ.get('METRIC_FETCH_LIMIT', '20'))

# Default plugins are used if the user has not specified.
CABOT_PLUGINS_ENABLED = os.environ.get('CABOT_PLUGINS_ENABLED',
                                       ','.join(['cabot_alert_hipchat',
                                                 'cabot_alert_mattermost',
                                                 'cabot_alert_twilio',
                                                 'cabot_alert_email',
                                                 'cabot_alert_pagerduty'])
                                       )
