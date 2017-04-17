from elasticsearch import Elasticsearch


def create_es_client(urls):
    """
    Create an elasticsearch-py client
    :param urls: comma-separated string of urls
    :return: a new elasticsearch-py client
    """
    urls = [url.strip() for url in urls.split(',')]
    return Elasticsearch(urls)
