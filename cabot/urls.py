from django.conf.urls import patterns, include, url
from django.conf import settings
from cabot.cabotapp.views import (
        run_status_check, graphite_api_data, checks_run_recently,
        StatusCheckDeleteView, StatusCheckListView, StatusCheckDetailView,
        StatusCheckResultDetailView, StatusCheckReportView, UserProfileUpdateAlert,
        duplicate_instance)

from cabot.cabotapp.views import (InstanceListView, InstanceDetailView,
        InstanceUpdateView, InstanceCreateView, InstanceDeleteView,
        ServiceListView, ServiceDetailView,
        ServiceUpdateView, ServiceCreateView, ServiceDeleteView,
        UserProfileUpdateView, ShiftListView, subscriptions)

from cabot.checks.views import CheckCreateView

from cabot import rest_urls

from django.contrib import admin
from django.views.generic.base import RedirectView
from django.contrib.auth.views import login, logout, password_reset, password_reset_done, password_reset_confirm
admin.autodiscover()

from importlib import import_module
import logging

logger = logging.getLogger(__name__)

urlpatterns = patterns('',
    url(r'^$', view=RedirectView.as_view(url='services/', permanent=False),
         name='dashboard'),
    url(r'^subscriptions/', view=subscriptions,
         name='subscriptions'),
    url(r'^accounts/login/', view=login, name='login'),
    url(r'^accounts/logout/', view=logout, name='logout'),
    url(r'^accounts/password-reset/',
         view=password_reset, name='password-reset'),
    url(r'^accounts/password-reset-done/',
         view=password_reset_done, name='password-reset-done'),
    url(r'^accounts/password-reset-confirm/',
         view=password_reset_confirm, name='password-reset-confirm'),
    url(r'^status/', view=checks_run_recently,
         name='system-status'),

    url(r'^services/', view=ServiceListView.as_view(),
         name='services'),
    url(r'^service/create/', view=ServiceCreateView.as_view(),
         name='create-service'),
    url(r'^service/update/(?P<pk>\d+)/',
         view=ServiceUpdateView.as_view(
         ), name='update-service'),
    url(r'^service/delete/(?P<pk>\d+)/',
         view=ServiceDeleteView.as_view(
         ), name='delete-service'),
    url(r'^service/(?P<pk>\d+)/',
         view=ServiceDetailView.as_view(), name='service'),

    url(r'^instances/', view=InstanceListView.as_view(),
         name='instances'),
    url(r'^instance/create/', view=InstanceCreateView.as_view(),
         name='create-instance'),
    url(r'^instance/update/(?P<pk>\d+)/',
         view=InstanceUpdateView.as_view(
         ), name='update-instance'),
    url(r'^instance/duplicate/(?P<pk>\d+)/',
         view=duplicate_instance, name='duplicate-instance'),
    url(r'^instance/delete/(?P<pk>\d+)/',
         view=InstanceDeleteView.as_view(
         ), name='delete-instance'),
    url(r'^instance/(?P<pk>\d+)/',
         view=InstanceDetailView.as_view(), name='instance'),

    url(r'^checks/$', view=StatusCheckListView.as_view(),
         name='checks'),
    url(r'^checks/create/(?P<plugin_name>.+)$', view=CheckCreateView.as_view(),
         name='create-check'),
    
    url(r'^check/run/(?P<pk>\d+)/',
         view=run_status_check, name='run-check'),
    url(r'^check/delete/(?P<pk>\d+)/',
         view=StatusCheckDeleteView.as_view(
         ), name='delete-check'),
    url(r'^check/(?P<pk>\d+)/',
         view=StatusCheckDetailView.as_view(), name='check'),
    url(r'^checks/report/$',
         view=StatusCheckReportView.as_view(), name='checks-report'),

    url(r'^shifts/', view=ShiftListView.as_view(),
         name='shifts'),

    url(r'^graphite/', view=graphite_api_data,
         name='graphite-data'),

    url(r'^user/(?P<pk>\d+)/profile/$',
         view=UserProfileUpdateView.as_view(), name='user-profile'),
    url(r'^user/(?P<pk>\d+)/profile/(?P<alerttype>.+)',
            view=UserProfileUpdateAlert.as_view(
            ), name='update-alert-user-data'),

    url(r'^admin/', include(admin.site.urls)),

    # Comment below line to disable browsable rest api
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    url(r'^api/', include(rest_urls.router.urls)),
    )

def append_plugin_urls():
    """
    Appends plugin specific URLs to the urlpatterns variable.
    """
    global urlpatterns
    for plugin in settings.CABOT_PLUGINS_ENABLED_PARSED:
        try:
            _module = import_module('%s.urls' % plugin)
        except Exception as e:
            logger.error('No url file available for plugin %s' % plugin)
        else:
            urlpatterns += patterns('',
                url(r'^plugins/%s/' % plugin, include('%s.urls' % plugin))
                )

append_plugin_urls()