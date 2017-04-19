from django.test import TestCase
from cabot.metricsapp.models import ElasticsearchSource


class TestElasticsearchSource(TestCase):
    def setUp(self):
        self.es_source = ElasticsearchSource.objects.create(
            name='elastigirl',
            urls='localhost',
            index='i'
        )

    def test_client(self):
        client = self.es_source.client
        self.assertIn('localhost', repr(client))

    def test_multiple_clients(self):
        self.es_source.urls = 'localhost,127.0.0.1'
        self.es_source.save()
        client = self.es_source.client
        self.assertIn('localhost', repr(client))
        self.assertIn('127.0.0.1', repr(client))

    def test_client_whitespace(self):
        """Whitespace should be stripped from the urls"""
        self.es_source.urls = '\nlocalhost,       globalhost'
        self.es_source.save()
        client = self.es_source.client
        self.assertIn('localhost', repr(client))
        self.assertIn('globalhost', repr(client))
        self.assertNotIn('\nlocalhost', repr(client))
        self.assertNotIn(' globalhost', repr(client))
