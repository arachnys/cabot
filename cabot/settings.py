import os
import dj_database_url
import re
from django.conf import settings
from django.core.urlresolvers import reverse_lazy
from cabot.settings_utils import environ_get_list, force_bool
from cabot.celeryconfig import *
from cabot.cabot_config import *

settings_dir = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(settings_dir)

DEBUG = force_bool(os.environ.get('DEBUG', False))

ADMINS = (
    ('Admin', os.environ.get('ADMIN_EMAIL', 'name@example.com')),
)

MANAGERS = ADMINS

if os.environ.get('CABOT_FROM_EMAIL'):
    DEFAULT_FROM_EMAIL = os.environ['CABOT_FROM_EMAIL']

DATABASES = {'default': dj_database_url.config()}

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

URL_PREFIX = os.environ.get('URL_PREFIX', '/').rstrip('/')

LOGIN_URL = reverse_lazy('login')

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
MEDIA_URL = '%s/media/' % URL_PREFIX

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, '.collectstatic/')

COMPRESS_ROOT = STATIC_ROOT

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '%s/static/' % URL_PREFIX
COMPRESS_URL = STATIC_URL

# Additional locations of static files
STATICFILES_DIRS = [os.path.join(PROJECT_ROOT, 'static')]

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

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
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': (
        os.path.join(PROJECT_ROOT, 'templates'),
    ),
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

MIDDLEWARE_CLASSES = (
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'cabot.urls'
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
    'compressor',
    'polymorphic',
    'djcelery',
    'jsonify',
    'cabot.cabotapp',
    'rest_framework',
)

AUTH_USER_MODEL = 'auth.User'

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

# For the email settings we both accept old and new names
EMAIL_HOST = environ_get_list(['EMAIL_HOST', 'SES_HOST'], 'localhost')
EMAIL_PORT = int(environ_get_list(['EMAIL_PORT', 'SES_PORT'], 25))
EMAIL_HOST_USER = environ_get_list(['EMAIL_USER', 'SES_USER'], '')
EMAIL_HOST_PASSWORD = environ_get_list(['EMAIL_PASSWORD', 'SES_PASS'], '')
EMAIL_BACKEND = environ_get_list(
    ['EMAIL_BACKEND', 'SES_BACKEND'],
    'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_USE_TLS = force_bool(environ_get_list(['EMAIL_USE_TLS', 'SES_USE_TLS'], False))
EMAIL_USE_SSL = force_bool(environ_get_list(['EMAIL_USE_SSL', 'SES_USE_SSL'], not EMAIL_USE_TLS))

COMPRESS_OFFLINE = not DEBUG

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
            'class': 'logging.NullHandler',
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
            'filename': os.environ.get('LOG_FILE', '/dev/null'),
            'maxBytes': 1024 * 1024 * 25,  # 25 MB
            'backupCount': 5,
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'log_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'log_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console', 'log_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        # Catch All Logger -- Captures any other logging
        '': {
            'handlers': ['console', 'log_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}

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
    'django.contrib.auth.backends.ModelBackend',
)

AUTH_LDAP = force_bool(os.environ.get('AUTH_LDAP', False))

if AUTH_LDAP:
    from settings_ldap import *
    AUTHENTICATION_BACKENDS += tuple(['django_auth_ldap.backend.LDAPBackend'])

EXPOSE_USER_API = force_bool(os.environ.get('EXPOSE_USER_API', False))
