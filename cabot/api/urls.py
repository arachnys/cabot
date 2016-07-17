from django.conf.urls import url, include
from rest_framework import routers, serializers, viewsets, mixins
from .views import ServiceViewSet, InstanceViewSet, ShiftViewSet, StatusCheckViewSet
from . import legacy_views

import logging
logger = logging.getLogger(__name__)

router = routers.DefaultRouter()
router.register(r'services', ServiceViewSet, base_name='service')
router.register(r'instances', InstanceViewSet, base_name='instance')
router.register(r'shifts', ShiftViewSet, base_name='shift')
router.register(r'checks', StatusCheckViewSet, base_name='statuscheck')

# Legacy
router.register(r'http_checks', legacy_views.HttpStatusCheckViewSet, base_name='http_checks')
router.register(r'icmp_checks', legacy_views.ICMPStatusCheckViewSet, base_name='icmp_checks')
router.register(r'jenkins_checks', legacy_views.JenkinsStatusCheckViewSet, base_name='jenkins_checks')
router.register(r'graphite_checks', legacy_views.GraphiteStatusCheckViewSet, base_name='graphite_checks')


urlpatterns = [
    url(r'^', include(router.urls)),
    ]

