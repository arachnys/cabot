from django.conf.urls import patterns, include, url
from django.conf import settings
from cabot.cabotapp.views import (
    checks_run_recently, acknowledge_alert, remove_acknowledgement,
    run_status_check,
    StatusCheckDeleteView, StatusCheckListView, StatusCheckDetailView,
    StatusCheckResultDetailView, StatusCheckReportView, UpdateUserView,
    UpdateUserAlertPluginDataView, InstanceListView, InstanceDetailView,
    InstanceUpdateView, InstanceCreateView, InstanceDeleteView,
    ServiceListView, ServiceDetailView, StatusCheckCreateView, StatusCheckUpdateView,
    ServiceUpdateView, ServiceCreateView, ServiceDeleteView,
    ShiftListView, subscriptions, PluginListView, PluginDetailView,
    duplicate_instance, duplicate_check)

from django.contrib import admin
from django.views.generic.base import RedirectView
from django.contrib.auth.views import login, logout, password_reset, password_reset_done, password_reset_confirm
admin.autodiscover()

from importlib import import_module
import logging

logger = logging.getLogger(__name__)

urlpatterns = patterns('',
    # Index Redirect
    url(r'^$', view=RedirectView.as_view(url='services/', permanent=False),
            name='dashboard'),

    #
    # Accounts
    #
    url(r'^accounts/login/', view=login, name='login'),
    url(r'^accounts/logout/', view=logout, name='logout'),
    url(r'^accounts/password-reset/',
            view=password_reset, name='password-reset'),
    url(r'^accounts/password-reset-done/',
            view=password_reset_done, name='password-reset-done'),
    url(r'^accounts/password-reset-confirm/',
            view=password_reset_confirm, name='password-reset-confirm'),
    # for the password reset views
    url('^', include('django.contrib.auth.urls')),

    #
    # Cabot Status
    #
    url(r'^status/', view=checks_run_recently,
            name='system-status'),

    #
    # Services
    #
    url(r'^services/', view=ServiceListView.as_view(),
            name='services'),
    url(r'^service/(?P<pk>\d+)/',
            view=ServiceDetailView.as_view(), name='service'),
    url(r'^service/create/', view=ServiceCreateView.as_view(),
            name='create-service'),
    url(r'^service/update/(?P<pk>\d+)/',
            view=ServiceUpdateView.as_view(
            ), name='update-service'),
    url(r'^service/delete/(?P<pk>\d+)/',
            view=ServiceDeleteView.as_view(
            ), name='delete-service'),
    url(r'^service/acknowledge_alert/(?P<pk>\d+)/',
            view=acknowledge_alert, name='acknowledge-alert'),
    url(r'^service/remove_acknowledgement/(?P<pk>\d+)/',
            view=remove_acknowledgement, name='remove-acknowledgement'),

    #
    # Instances
    #
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
    #
    # Checks
    #
    url(r'^checks/$', view=StatusCheckListView.as_view(),
            name='checks'),
    url(r'^checks/create/$', view=StatusCheckCreateView.as_view(),
            name='checks-create'),
    url(r'^check/run/(?P<pk>\d+)/',
            view=run_status_check, name='run-check'),
    url(r'^check/delete/(?P<pk>\d+)/',
            view=StatusCheckDeleteView.as_view(
            ), name='delete-check'),
    url(r'^check/update/(?P<pk>\d+)/',
            view=StatusCheckUpdateView.as_view(
            ), name='update-check'),
    url(r'^check/duplicate/(?P<pk>\d+)/',
            view=duplicate_check , name='duplicate-check'),
    url(r'^check/(?P<pk>\d+)/',
            view=StatusCheckDetailView.as_view(), name='check'),
    url(r'^checks/report/$',
            view=StatusCheckReportView.as_view(), name='checks-report'),

    #
    # Plugins
    #
    url(r'^plugins/$', view=PluginListView.as_view(),
            name='plugins'),
    url(r'^plugins/(?P<pk>\d+)/',
            view=PluginDetailView.as_view(), name='plugin'),


    #
    # Status Check Results
    #
    url(r'^result/(?P<pk>\d+)/',
            view=StatusCheckResultDetailView.as_view(
            ), name='result'),

    url(r'^shifts/', view=ShiftListView.as_view(),
            name='shifts'),

    #
    # User Settings
    #
    url(r'^user/(?P<pk>\d+)/General/',
            view=UpdateUserView.as_view(), name='update-user'),
    url(r'^user/(?P<pk>\d+)/plugin/(?P<alert_plugin_pk>\d+)',
               view=UpdateUserAlertPluginDataView.as_view(
               ), name='update-user-userdata'),
    url(r'^subscriptions/', view=subscriptions,
            name='subscriptions'),

    #
    # Admin
    #
    url(r'^admin/', include(admin.site.urls)),


    # API. Comment out these lines to disable the browsable api
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api/', include('cabot.api.urls', namespace='api')),
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
            pass
        else:
            urlpatterns += patterns('',
                url(r'^plugins/%s/' % plugin, include('%s.urls' % plugin))
                )

append_plugin_urls()
