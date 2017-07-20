import json
from django.db.models.signals import pre_save
from django.dispatch import receiver
from cabot.metricsapp.api import adjust_time_range
from cabot.metricsapp.models import ElasticsearchStatusCheck


@receiver(pre_save, dispatch_uid="adjust_query_time_range", sender=ElasticsearchStatusCheck)
def adjust_query_time_range(sender, instance, *args, **kwargs):
    instance.queries = json.dumps(adjust_time_range(json.loads(instance.queries), instance.time_range))
