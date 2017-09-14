import sys

from django.core.urlresolvers import reverse, clear_url_caches
from django.conf import settings
from django.test.utils import override_settings
from importlib import import_module

from rest_framework import status, HTTP_HEADER_ENCODING

from tests_basic import LocalTestCase

class override_local_settings(override_settings):
    def clear_cache(self):
        # If we don't do this, nothing gets correctly set for the URL Prefix
        urlconf = settings.ROOT_URLCONF
        if urlconf in sys.modules:
            reload(sys.modules[urlconf])
        import_module(urlconf)

        # Don't forget to clear out the cache for `reverse`
        clear_url_caches()

    def __init__(self, urlprefix, custom_check_plugins):
        urlprefix = urlprefix.rstrip("/")
        installed_apps = settings.INSTALLED_APPS
        installed_apps += tuple(custom_check_plugins)

        # Have to turn off the compressor here, can't find a way to reload
        # the COMPRESS_URL into it on the fly
        super(override_local_settings, self).__init__(
            URL_PREFIX=urlprefix,
            MEDIA_URL="%s/media/" % urlprefix,
            STATIC_URL="%s/static/" % urlprefix,
            COMPRESS_URL="%s/static/" % urlprefix,
            COMPRESS_ENABLED=False,
            COMPRESS_PRECOMPILERS=(),
            INSTALLED_APPS=installed_apps
        )

    def __enter__(self):
        super(override_local_settings, self).__enter__()
        self.clear_cache()

    def __exit__(self, exc_type, exc_value, traceback):
        super(override_local_settings, self).__exit__(exc_type, exc_value, traceback)
        self.clear_cache()

def set_url_prefix_and_custom_check_plugins(prefix, plugins):
    return override_local_settings(prefix, plugins)

class URLPrefixTestCase(LocalTestCase):
    def set_url_prefix(self, prefix):
        return override_local_settings(prefix, [])

    def test_reverse(self):
        prefix = '/test'
        before = reverse('services')

        with self.set_url_prefix(prefix):
            self.assertNotEqual(reverse('services'), before)
            self.assertTrue(reverse('services').startswith(prefix))
            self.assertEqual(reverse('services')[len(prefix):], before)

    def test_loginurl(self):
        prefix = '/test'

        with self.set_url_prefix(prefix):
            loginurl = str(settings.LOGIN_URL)
            response = self.client.get(reverse('services'))

            self.assertTrue(loginurl.startswith(prefix))
            self.assertTrue(loginurl in response.url)

    def test_query(self):
        prefix = '/test'
        self.client.login(username=self.username, password=self.password)

        before_services = self.client.get(reverse('services'))
        before_systemstatus = self.client.get(reverse('system-status'))

        with self.set_url_prefix(prefix):
            response = self.client.get(reverse('services'))

            self.assertEqual(response.status_code, before_services.status_code)
            self.assertNotEqual(response.content, before_services.content)

            self.assertIn(reverse('services'), response.content)

            response_systemstatus = self.client.get(reverse('system-status'))

            self.assertEqual(response_systemstatus.status_code, before_systemstatus.status_code)
