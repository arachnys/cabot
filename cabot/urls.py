from django.conf.urls import include, url
from django.conf import settings
from cabot.cabotapp.views import (
    about, run_status_check, graphite_api_data, checks_run_recently,
    duplicate_icmp_check, duplicate_graphite_check, duplicate_http_check, duplicate_jenkins_check,
    duplicate_instance, acknowledge_alert, remove_acknowledgement,
    GraphiteCheckCreateView, GraphiteCheckUpdateView,
    HttpCheckCreateView, HttpCheckUpdateView,
    ICMPCheckCreateView, ICMPCheckUpdateView,
    JenkinsCheckCreateView, JenkinsCheckUpdateView,
    StatusCheckDeleteView, StatusCheckListView, StatusCheckDetailView,
    StatusCheckResultDetailView, StatusCheckReportView, UserProfileUpdateAlert,
    PluginSettingsView, AlertTestView, AlertTestPluginView, SetupView, OnCallView)

from cabot.cabotapp.views import (InstanceListView, InstanceDetailView,
    InstanceUpdateView, InstanceCreateView, InstanceDeleteView,
    ServiceListView, ServicePublicListView, ServiceDetailView,
    ServiceUpdateView, ServiceCreateView, ServiceDeleteView,
    UserProfileUpdateView, ShiftListView, subscriptions)

from cabot.cabotapp.utils import cabot_needs_setup

from cabot import rest_urls
from rest_framework.documentation import include_docs_urls

from django.contrib import admin
from django.views.generic.base import RedirectView
from django.views.static import serve
from django.shortcuts import redirect
from django.contrib.auth.views import login, logout, password_reset, password_reset_done, password_reset_confirm
admin.autodiscover()

from importlib import import_module
import logging
import os

logger = logging.getLogger(__name__)

def first_time_setup_wrapper(func):
    def wrapper(*args, **kwargs):
        if cabot_needs_setup():
            return redirect('first_time_setup')
        else:
            return func(*args, **kwargs)
    return wrapper


def home_authentication_switcher(request, *args, **kwargs):
    if cabot_needs_setup():
        return redirect('first_time_setup')
    if not request.user.is_authenticated():
        return ServicePublicListView.as_view()(request, *args, **kwargs)
    else:
        return ServiceListView.as_view()(request, *args, **kwargs)

urlpatterns = [
     # for the password reset views
     url('^', include('django.contrib.auth.urls')),

     url(r'^(?P<path>favicon\.ico)$', serve, name='favicon',
        kwargs={'document_root': os.path.join(settings.STATIC_ROOT, 'arachnys/img')}),

     url(r'^$', view=home_authentication_switcher,
        name='dashboard'),
     url(r'^subscriptions/', view=subscriptions,
        name='subscriptions'),
     url(r'^accounts/login/', view=first_time_setup_wrapper(login), name='login'),
     url(r'^accounts/logout/', view=logout, name='logout'),
     url(r'^setup/', view=SetupView.as_view(), name='first_time_setup'),
     url(r'^accounts/password-reset/',
        view=password_reset, name='password-reset'),
     url(r'^accounts/password-reset-done/',
        view=password_reset_done, name='password-reset-done'),
     url(r'^accounts/password-reset-confirm/',
        view=password_reset_confirm, name='password-reset-confirm'),
     url(r'^status/', view=checks_run_recently,
        name='system-status'),
     url(r'^about/', view=about,
        name='about-cabot'),

     url(r'^services/', view=ServiceListView.as_view(),
        name='services'),
     url(r'^public/', view=ServicePublicListView.as_view(),
        name='public'),
     url(r'^service/create/', view=ServiceCreateView.as_view(),
        name='create-service'),
     url(r'^service/update/(?P<pk>\d+)/',
        view=ServiceUpdateView.as_view(), name='update-service'),
     url(r'^service/delete/(?P<pk>\d+)/',
        view=ServiceDeleteView.as_view(), name='delete-service'),
     url(r'^service/(?P<pk>\d+)/',
        view=ServiceDetailView.as_view(), name='service'),
     url(r'^service/acknowledge_alert/(?P<pk>\d+)/',
        view=acknowledge_alert, name='acknowledge-alert'),
     url(r'^service/remove_acknowledgement/(?P<pk>\d+)/',
        view=remove_acknowledgement, name='remove-acknowledgement'),

     url(r'^instances/', view=InstanceListView.as_view(),
        name='instances'),
     url(r'^instance/create/', view=InstanceCreateView.as_view(),
        name='create-instance'),
     url(r'^instance/update/(?P<pk>\d+)/',
        view=InstanceUpdateView.as_view(), name='update-instance'),
     url(r'^instance/duplicate/(?P<pk>\d+)/',
        view=duplicate_instance, name='duplicate-instance'),
     url(r'^instance/delete/(?P<pk>\d+)/',
        view=InstanceDeleteView.as_view(), name='delete-instance'),
     url(r'^instance/(?P<pk>\d+)/',
        view=InstanceDetailView.as_view(), name='instance'),

     url(r'^checks/$', view=StatusCheckListView.as_view(),
        name='checks'),
     url(r'^check/run/(?P<pk>\d+)/',
        view=run_status_check, name='run-check'),
     url(r'^check/delete/(?P<pk>\d+)/',
        view=StatusCheckDeleteView.as_view(), name='delete-check'),
     url(r'^check/(?P<pk>\d+)/',
        view=StatusCheckDetailView.as_view(), name='check'),
     url(r'^checks/report/$',
        view=StatusCheckReportView.as_view(), name='checks-report'),

     url(r'^icmpcheck/create/', view=ICMPCheckCreateView.as_view(),
        name='create-icmp-check'),
     url(r'^icmpcheck/update/(?P<pk>\d+)/',
        view=ICMPCheckUpdateView.as_view(), name='update-icmp-check'),
     url(r'^icmpcheck/duplicate/(?P<pk>\d+)/',
        view=duplicate_icmp_check, name='duplicate-icmp-check'),
     url(r'^graphitecheck/create/',
        view=GraphiteCheckCreateView.as_view(), name='create-graphite-check'),
     url(r'^graphitecheck/update/(?P<pk>\d+)/',
        view=GraphiteCheckUpdateView.as_view(), name='update-graphite-check'),
     url(r'^graphitecheck/duplicate/(?P<pk>\d+)/',
        view=duplicate_graphite_check, name='duplicate-graphite-check'),
     url(r'^httpcheck/create/', view=HttpCheckCreateView.as_view(),
        name='create-http-check'),
     url(r'^httpcheck/update/(?P<pk>\d+)/',
        view=HttpCheckUpdateView.as_view(), name='update-http-check'),
     url(r'^httpcheck/duplicate/(?P<pk>\d+)/',
        view=duplicate_http_check, name='duplicate-http-check'),
     url(r'^jenkins_check/create/', view=JenkinsCheckCreateView.as_view(),
        name='create-jenkins-check'),
     url(r'^jenkins_check/update/(?P<pk>\d+)/',
        view=JenkinsCheckUpdateView.as_view(), name='update-jenkins-check'),
     url(r'^jenkins_check/duplicate/(?P<pk>\d+)/',
        view=duplicate_jenkins_check,
        name='duplicate-jenkins-check'),

     url(r'^result/(?P<pk>\d+)/',
        view=StatusCheckResultDetailView.as_view(), name='result'),
     url(r'^shifts/', view=ShiftListView.as_view(),
        name='shifts'),
     url(r'^graphite/', view=graphite_api_data,
        name='graphite-data'),
     url(r'^user/(?P<pk>\d+)/profile/$',
        view=UserProfileUpdateView.as_view(), name='user-profile'),
     url(r'^alert-test/$',
        view=AlertTestView.as_view(), name='alert-test'),
     url(r'^alert-test-plugin/$',
        view=AlertTestPluginView.as_view(), name='alert-test-plugin'),
     url(r'^plugin-settings/$',
        view=RedirectView.as_view(url='global/', permanent=False), name='plugin-settings-global'),
     url(r'^plugin-settings/(?P<plugin_name>.+)/$',
        view=PluginSettingsView.as_view(), name='plugin-settings'),
     url(r'^user/(?P<pk>\d+)/profile/(?P<alerttype>.+)/',
        view=UserProfileUpdateAlert.as_view(), name='update-alert-user-data'),
     url(r'^admin/', include(admin.site.urls)),
     # Comment below line to disable browsable rest api
     url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
     url(r'^api/', include(rest_urls.router.urls)),
     url(r'^api/oncall', view=OnCallView.as_view(), name='oncall'),
     url(r'^docs/', include_docs_urls(title="Cabot API", description="An API to create and view Cabot checks and services."))
]

def append_plugin_urls():
    """
    Appends plugin specific URLs to the urlpatterns variable.
    """
    global urlpatterns
    for plugin in settings.CABOT_PLUGINS_ENABLED_PARSED:
        try:
            _module = import_module('%s.urls' % plugin)
        except ImportError:
            pass
        else:
            urlpatterns += [
                url(r'^plugins/%s/' % plugin, include('%s.urls' % plugin))
            ]


append_plugin_urls()

if settings.AUTH_SOCIAL:
    urlpatterns += [
        url('', include('social_django.urls', namespace='social'))
    ]

if settings.URL_PREFIX.strip('/'):
    urlpatterns = [
        url(r'^%s/' % settings.URL_PREFIX.strip('/'), include(urlpatterns))
    ]
