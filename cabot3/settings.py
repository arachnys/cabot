import os
import re
from django.conf import settings
from django.urls import reverse_lazy
from cabot3.settings_utils import environ_get_list, force_bool
from cabot3.cabot_config import *
import environ

# reading .env file
environ.Env.read_env()

settings_dir = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(settings_dir)
 
DEBUG=os.environ.get('DEBUG', False)

PROD=os.environ.get('PROD', False)


ADMINS = (
    ('Admin', os.environ.get('ADMIN_EMAIL', 'name@example.com')),
)

MANAGERS = ADMINS

if os.environ.get('CABOT_FROM_EMAIL'):
    DEFAULT_FROM_EMAIL = os.environ.get('CABOT_FROM_EMAIL', 'admin@example.com')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DATABASE_NAME', 'cabot'),
        'USER': os.environ.get('DATABASE_USER', 'root'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', 'root'),
        'HOST': os.environ.get('DATABASE_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DATABASE_PORT', '3306'),
    }
}

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

URL_PREFIX = os.environ.get('URL_PREFIX', '/').rstrip('/')

LOGIN_URL = os.environ.get('LOGIN_URL', reverse_lazy('login'))
LOGIN_REDIRECT_URL = reverse_lazy('services')

USE_TZ = True

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = os.environ.get('TIME_ZONE','America/Argentina/Buenos_Aires')
# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'es'

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

if os.environ.get('WWW_SCHEME', 'http') == 'https':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

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
            'cabot3.context_processors.global_settings',
        ],
        'debug': force_bool(os.environ.get('TEMPLATE_DEBUG', False))
    },
}]

MIDDLEWARE = (


    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'cabot3.urls'
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'django_filters',
    'compressor',
    'polymorphic',
    'jsonify',
    'cabot3.cabotapp',
    'rest_framework',
    'dal',
    'dal_select2',
    'django.contrib.admin',
    'bootstrapform',
    'django_celery_beat', 
)

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379')
CELERY_BEAT_SCHEDULER = os.environ.get('CELERY_BEAT_SCHEDULER', 'django_celery_beat.schedulers:DatabaseScheduler')

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

timezone = os.environ.get('TIME_ZONE', 'America/Argentina/Buenos_Aires')

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
AUTH_USER_MODEL = 'auth.User'

# Load additional apps from configuration file
CABOT_PLUGINS_ENABLED_PARSED = []

#You can add plugins in 'CABOT_PLUGINS' replace None by list with plugin names
CABOT_PLUGINS = os.environ.get('CABOT_PLUGINS', None) 

if CABOT_PLUGINS != None:
    for plugin in CABOT_PLUGINS.split(","):
        # Hack to clean up if versions of plugins specified
        exploded = re.split(r'[<>=]+', plugin)
        CABOT_PLUGINS_ENABLED_PARSED.append(exploded[0])



INSTALLED_APPS += tuple(CABOT_PLUGINS_ENABLED_PARSED)


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
            'handlers': ['console', 'log_file'],
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
        'django_filters.rest_framework.DjangoFilterBackend',
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

# Github SSO
AUTH_GITHUB_ENTERPRISE_ORG = force_bool(os.environ.get('AUTH_GITHUB_ENTERPRISE_ORG', False))
AUTH_GITHUB_ORG = force_bool(os.environ.get('AUTH_GITHUB_ORG', False))
AUTH_GOOGLE_OAUTH2 = force_bool(os.environ.get('AUTH_GOOGLE_OAUTH2', False))

AUTH_SOCIAL = AUTH_GITHUB_ORG or AUTH_GITHUB_ENTERPRISE_ORG or AUTH_GOOGLE_OAUTH2
SOCIAL_AUTH_REDIRECT_IS_HTTPS = force_bool(os.environ.get('SOCIAL_AUTH_REDIRECT_IS_HTTPS', False))

if AUTH_SOCIAL:
    SOCIAL_AUTH_URL_NAMESPACE = 'social'
    INSTALLED_APPS += tuple(['social_django'])

if AUTH_GITHUB_ORG:
    AUTHENTICATION_BACKENDS += tuple(['social_core.backends.github.GithubOrganizationOAuth2'])
    SOCIAL_AUTH_GITHUB_ORG_KEY = os.environ.get('AUTH_GITHUB_ORG_CLIENT_ID')
    SOCIAL_AUTH_GITHUB_ORG_SECRET = os.environ.get('AUTH_GITHUB_ORG_CLIENT_SECRET')
    SOCIAL_AUTH_GITHUB_ORG_NAME = os.environ.get('AUTH_GITHUB_ORG_NAME')
    SOCIAL_AUTH_GITHUB_ORG_SCOPE = ['read:org']

if AUTH_GITHUB_ENTERPRISE_ORG:
    AUTHENTICATION_BACKENDS += tuple(['social_core.backends.github_enterprise.GithubEnterpriseOrganizationOAuth2'])
    SOCIAL_AUTH_GITHUB_ENTERPRISE_ORG_URL = os.environ.get('AUTH_GITHUB_ENTERPRISE_ORG_URL')
    SOCIAL_AUTH_GITHUB_ENTERPRISE_ORG_API_URL = os.environ.get('AUTH_GITHUB_ENTERPRISE_ORG_API_URL')
    SOCIAL_AUTH_GITHUB_ENTERPRISE_ORG_KEY = os.environ.get('AUTH_GITHUB_ENTERPRISE_ORG_CLIENT_ID')
    SOCIAL_AUTH_GITHUB_ENTERPRISE_ORG_SECRET = os.environ.get('AUTH_GITHUB_ENTERPRISE_ORG_CLIENT_SECRET')
    SOCIAL_AUTH_GITHUB_ENTERPRISE_ORG_NAME = os.environ.get('AUTH_GITHUB_ENTERPRISE_ORG_NAME')

if AUTH_GOOGLE_OAUTH2:
    AUTHENTICATION_BACKENDS += tuple(['social_core.backends.google.GoogleOAuth2'])
    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('AUTH_GOOGLE_OAUTH2_KEY')
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('AUTH_GOOGLE_OAUTH2_SECRET')
    SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS = os.environ.get('AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS', '').split(',')

EXPOSE_USER_API = force_bool(os.environ.get('EXPOSE_USER_API', False))
ENABLE_SUBSCRIPTION = force_bool(os.environ.get('ENABLE_SUBSCRIPTION', True))
ENABLE_DUTY_ROTA = force_bool(os.environ.get('ENABLE_DUTY_ROTA', True))
