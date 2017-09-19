from django.db import models
import time
from cabot.metricsapp.models.base import MetricsSourceBase, MetricsStatusCheckBase
from celery.utils.log import get_task_logger


logger = get_task_logger(__name__)


class DummySource(MetricsSourceBase):
    """
    Dummy source to check if metrics check logic is working correctly.
    Doesn't actually do anything
    """
    class Meta:
        app_label = 'dummyapp'


class DummyStatusCheck(MetricsStatusCheckBase):
    """
    Dummy status check to check if metrics logic is working correctly.
    Uses data fixtures (alternating failure and success instead of getting
    data from a metrics source.
    """
    class Meta:
        app_label = 'dummyapp'

    @property
    def check_category(self):
        return "Dummy check"

    @property
    def description(self):
        return 'Test check--should never fail'

    update_url = 'check'

    icon = 'glyphicon glyphicon-remove'

    counter = models.IntegerField(default=0)

    def get_series(self):
        series = {
            'error': False,
            'raw': 'dummy data please ignore',
        }

        if self.counter % 2 == 0:
            # Even counts: passing (< 500)
            series['data'] = [{'series': 'dummy', 'datapoints': [[int(time.time()), 0],
                                                                 [int(time.time()) - 60, 0]]}]
        else:
            # Odd counts: failing (> 500)
            series['data'] = [{'series': 'dummy', 'datapoints': [[int(time.time()), 1000],
                                                                 [int(time.time()) - 60, 1000]]}]

        self.counter += 1
        self.save()
        return series
