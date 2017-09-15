from collections import defaultdict

from cabot.cabotapp.models import CheckGroupMixin, HttpStatusCheck, \
                                  JenkinsStatusCheck, TCPStatusCheck
from cabot.metricsapp.models import ElasticsearchStatusCheck


NORMAL_CHECK_QUEUE = 'normal_checks'
CRITICAL_CHECK_QUEUE = 'critical_checks'
DEFAULT_CHECK_QUEUE = NORMAL_CHECK_QUEUE

STATUS_CHECK_TO_QUEUE = \
    defaultdict(lambda: defaultdict(lambda: DEFAULT_CHECK_QUEUE), {
        HttpStatusCheck.check_category:
            defaultdict(lambda: DEFAULT_CHECK_QUEUE, {
                CheckGroupMixin.WARNING_STATUS: NORMAL_CHECK_QUEUE,
                CheckGroupMixin.ERROR_STATUS: NORMAL_CHECK_QUEUE,
                CheckGroupMixin.CRITICAL_STATUS: CRITICAL_CHECK_QUEUE,
            }),
        JenkinsStatusCheck.check_category:
            defaultdict(lambda: DEFAULT_CHECK_QUEUE, {
                CheckGroupMixin.WARNING_STATUS: NORMAL_CHECK_QUEUE,
                CheckGroupMixin.ERROR_STATUS: NORMAL_CHECK_QUEUE,
                CheckGroupMixin.CRITICAL_STATUS: CRITICAL_CHECK_QUEUE,
            }),
        TCPStatusCheck.check_category:
            defaultdict(lambda: DEFAULT_CHECK_QUEUE, {
                CheckGroupMixin.WARNING_STATUS: NORMAL_CHECK_QUEUE,
                CheckGroupMixin.ERROR_STATUS: NORMAL_CHECK_QUEUE,
                CheckGroupMixin.CRITICAL_STATUS: CRITICAL_CHECK_QUEUE,
            }),
        ElasticsearchStatusCheck.check_category:
            defaultdict(lambda: DEFAULT_CHECK_QUEUE, {
                CheckGroupMixin.WARNING_STATUS: NORMAL_CHECK_QUEUE,
                CheckGroupMixin.ERROR_STATUS: CRITICAL_CHECK_QUEUE,
                CheckGroupMixin.CRITICAL_STATUS: CRITICAL_CHECK_QUEUE,
            }),
    })
