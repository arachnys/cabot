from django.conf.urls import patterns, include, url
from cabot.cabotapp.views import (
    run_status_check, graphite_api_data, twiml_callback, checks_run_recently,
    duplicate_icmp_check, duplicate_graphite_check, duplicate_http_check, duplicate_jenkins_check, duplicate_instance,
    GraphiteCheckCreateView, GraphiteCheckUpdateView,
    HttpCheckCreateView, HttpCheckUpdateView,
    ICMPCheckCreateView, ICMPCheckUpdateView,
    JenkinsCheckCreateView, JenkinsCheckUpdateView,
    StatusCheckDeleteView, StatusCheckListView, StatusCheckDetailView,
    StatusCheckResultDetailView, StatusCheckReportView)

from cabot.cabotapp.views import (InstanceListView, InstanceDetailView,
                            InstanceUpdateView, InstanceCreateView, InstanceDeleteView,
                            ServiceListView, ServiceDetailView,
                            ServiceUpdateView, ServiceCreateView, ServiceDeleteView,
                            UserProfileUpdateView, ShiftListView, subscriptions)
from django.contrib import admin
from django.views.generic.base import RedirectView
from django.contrib.auth.views import login, logout, password_reset, password_reset_done, password_reset_confirm
admin.autodiscover()

from cabot import rest_urls

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
                       url(r'^check/run/(?P<pk>\d+)/',
                           view=run_status_check, name='run-check'),
                       url(r'^check/delete/(?P<pk>\d+)/',
                           view=StatusCheckDeleteView.as_view(
                           ), name='delete-check'),
                       url(r'^check/(?P<pk>\d+)/',
                           view=StatusCheckDetailView.as_view(), name='check'),
                       url(r'^checks/report/$',
                           view=StatusCheckReportView.as_view(), name='checks-report'),


                       url(r'^icmpcheck/create/', view=ICMPCheckCreateView.as_view(),
                           name='create-icmp-check'),
                       url(r'^icmpcheck/update/(?P<pk>\d+)/',
                           view=ICMPCheckUpdateView.as_view(
                           ), name='update-icmp-check'),
                       url(r'^icmpcheck/duplicate/(?P<pk>\d+)/',
                           view=duplicate_icmp_check, name='duplicate-icmp-check'),

                       url(r'^graphitecheck/create/',
                           view=GraphiteCheckCreateView.as_view(
                           ), name='create-graphite-check'),
                       url(r'^graphitecheck/update/(?P<pk>\d+)/',
                           view=GraphiteCheckUpdateView.as_view(
                           ), name='update-graphite-check'),
                       url(r'^graphitecheck/duplicate/(?P<pk>\d+)/',
                           view=duplicate_graphite_check, name='duplicate-graphite-check'),

                       url(r'^httpcheck/create/', view=HttpCheckCreateView.as_view(),
                           name='create-http-check'),
                       url(r'^httpcheck/update/(?P<pk>\d+)/',
                           view=HttpCheckUpdateView.as_view(
                           ), name='update-http-check'),
                       url(r'^httpcheck/duplicate/(?P<pk>\d+)/',
                           view=duplicate_http_check, name='duplicate-http-check'),

                       url(r'^jenkins_check/create/', view=JenkinsCheckCreateView.as_view(),
                           name='create-jenkins-check'),
                       url(r'^jenkins_check/update/(?P<pk>\d+)/',
                           view=JenkinsCheckUpdateView.as_view(
                           ), name='update-jenkins-check'),
                       url(r'^jenkins_check/duplicate/(?P<pk>\d+)/',
                           view=duplicate_jenkins_check, name='duplicate-jenkins-check'),

                       url(r'^result/(?P<service_id>\d+)/twiml_callback/',
                           view=twiml_callback, name='twiml-callback'),
                       url(r'^result/(?P<pk>\d+)/',
                           view=StatusCheckResultDetailView.as_view(
                           ), name='result'),

                       url(r'^shifts/', view=ShiftListView.as_view(),
                           name='shifts'),

                       url(r'^graphite/', view=graphite_api_data,
                           name='graphite-data'),

                       url(r'^user/(?P<pk>\d+)/profile/',
                           view=UserProfileUpdateView.as_view(
                           ), name='user-profile'),
                       url(r'^admin/', include(admin.site.urls)),

                       # Comment below line to disable browsable rest api
                       url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

                       url(r'^api/', include(rest_urls.router.urls)),
                       )
