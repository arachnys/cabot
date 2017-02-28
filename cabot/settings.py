import os
import dj_database_url
import re
from cabot.celeryconfig import *
from cabot.cabot_config import *
import logging
import sys
import xmlrunner
import pymysql
pymysql.install_as_MySQLdb()


settings_dir = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(settings_dir)

TEMPLATE_DEBUG = DEBUG = os.environ.get("DEBUG", False)

ADMINS = (
    ('Admin', os.environ.get('ADMIN_EMAIL', 'name@example.com')),
)

MANAGERS = ADMINS

DATABASES = {'default': dj_database_url.parse(os.environ["DATABASE_URL"])}

USE_TZ = True

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = os.environ.get('TIME_ZONE', 'Etc/UTC')

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, os.path.pardir, 'static/')

COMPRESS_ROOT = STATIC_ROOT

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = [os.path.join(PROJECT_ROOT, 'static')]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY', '2FL6ORhHwr5eX34pP9mMugnIOd3jzVuT45f7w430Mt5PnEwbcJgma0q8zUXNZ68A')

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'social.apps.django_app.middleware.SocialAuthExceptionMiddleware',
    'rollbar.contrib.django.middleware.RollbarNotifierMiddleware',
)

ROOT_URLCONF = 'cabot.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'south',
    'compressor',
    'polymorphic',
    'djcelery',
    'mptt',
    'jsonify',
    'cabot.cabotapp',
    'rest_framework',
    'social.apps.django_app.default',
)

# Load additional apps from configuration file
CABOT_PLUGINS_ENABLED_PARSED = []
for plugin in CABOT_PLUGINS_ENABLED.split(","):
    # Hack to clean up if versions of plugins specified
    exploded = re.split(r'[<>=]+', plugin)
    CABOT_PLUGINS_ENABLED_PARSED.append(exploded[0])

INSTALLED_APPS += tuple(CABOT_PLUGINS_ENABLED_PARSED)

COMPRESS_PRECOMPILERS = (
    ('text/coffeescript', 'coffee --compile --stdio'),
    ('text/eco',
     'eco -i TEMPLATES {infile} && cat "$(echo "{infile}" | sed -e "s/\.eco$/.js/g")"'),
    ('text/less', 'lessc {infile} > {outfile}'),
)

EMAIL_HOST = os.environ.get('SES_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('SES_PORT', 25))
EMAIL_HOST_USER = os.environ.get('SES_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('SES_PASS', '')
EMAIL_BACKEND = os.environ.get('SES_BACKEND', 'django_smtp_ssl.SSLEmailBackend')

COMPRESS_OFFLINE = not DEBUG

COMPRESS_URL = '/static/'

RECOVERY_SNIPPETS_WHITELIST = (
    r'https?://[^.]+\.hackpad\.com/[^./]+\.js',
    r'https?://gist\.github\.com/[^.]+\.js',
    r'https?://www\.refheap\.com/[^.]+\.js',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.environ['LOG_FILE'],
            'maxBytes': 1024 * 1024 * 25,  # 25 MB
            'backupCount': 5,
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'rollbar': {
            'level': 'ERROR',
            'class': 'rollbar.logger.RollbarHandler',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'log_file', 'mail_admins', 'rollbar'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'log_file', 'mail_admins', 'rollbar'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console', 'log_file', 'mail_admins', 'rollbar'],
            'level': 'INFO',
            'propagate': False,
        },
        # Catch All Logger -- Captures any other logging
        '': {
            'handlers': ['console', 'log_file', 'mail_admins', 'rollbar'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}

# Disable logging for tests
if len(sys.argv) > 1 and sys.argv[1] == 'test':
    logging.disable(logging.CRITICAL)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissions',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
    ]
}

AUTHENTICATION_BACKENDS = (
    'social.backends.google.GoogleOAuth2',
    'social.backends.google.GoogleOAuth',
    'django.contrib.auth.backends.ModelBackend',
)

AUTH_LDAP = os.environ.get('AUTH_LDAP', 'false')

if AUTH_LDAP.lower() == "true":
    from settings_ldap import *
    AUTHENTICATION_BACKENDS += tuple(['django_auth_ldap.backend.LDAPBackend'])


_TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'social.apps.django_app.context_processors.backends',
    'social.apps.django_app.context_processors.login_redirect',
)

SOCIAL_AUTH_AUTHENTICATION_BACKENDS = (
    'social.backends.google.GoogleOAuth2',
    'social.backends.google.GoogleOAuth',
)

SOCIAL_AUTH_USER_MODEL = 'auth.User'
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['username', 'first_name', 'email']
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True
SOCIAL_AUTH_URL_NAMESPACE = 'social'
SOCIAL_AUTH_RAISE_EXCEPTIONS = True
RAISE_EXCEPTIONS = True

SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS = os.environ.get('OAUTH2_WHITELISTED_DOMAINS', 'example.com').split(',')
GOOGLE_OAUTH2_SOCIAL_AUTH_RAISE_EXCEPTIONS = True
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('GOOGLE_OAUTH2_SECRET')
COMPRESS_ENABLED = False
LOGIN_REDIRECT_URL = '/'

# Use cloudwatch to monitor cabot alerts
AWS_CLOUDWATCH_SYNC = os.environ.get('AWS_CLOUDWATCH_SYNC', False)
AWS_CLOUDWATCH_REGION = os.environ.get('AWS_CLOUDWATCH_REGION', 'us-east-1')
AWS_CLOUDWATCH_ACCESS_KEY = os.environ.get('AWS_CLOUDWATCH_ACCESS_KEY', None)
AWS_CLOUDWATCH_SECRET_KEY = os.environ.get('AWS_CLOUDWATCH_SECRET_KEY', None)
AWS_CLOUDWATCH_PREFIX = os.environ.get('AWS_CLOUDWATCH_PREFIX', None)
AWS_CLOUDWATCH_NAMESPACE = os.environ.get('AWS_CLOUDWATCH_NAMESPACE', 'Cabot')

# Rollbar settings
ROLLBAR = {
    'access_token': os.environ.get('ROLLBAR_ACCESS_TOKEN', None),
    'environment': os.environ.get('ROLLBAR_ENVIRONMENT', 'prod'),
    'branch': os.environ.get('ROLLBAR_BRANCH', 'master'),
    'root': PROJECT_ROOT,
}

CELERYD_HIJACK_ROOT_LOGGER = False

# Image for service page
SERVICE_IMAGE = os.environ.get('SERVICE_IMAGE', None)
# xml output for tests
TEST_RUNNER = 'xmlrunner.extra.djangotestrunner.XMLTestRunner'
TEST_OUTPUT_DIR = os.environ.get('TEST_OUTPUT_DIR', '.')

