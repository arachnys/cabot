from django.conf.urls.defaults import patterns, include, url
from cabotapp.views import (run_status_check, update_service,
    graphite_api_data, twiml_callback, checks_run_recently,
    GraphiteCheckCreateView, GraphiteCheckUpdateView,
    HttpCheckCreateView, HttpCheckUpdateView,
    JenkinsCheckCreateView, JenkinsCheckUpdateView,
    StatusCheckDeleteView, StatusCheckListView, StatusCheckDetailView,
    StatusCheckResultDetailView)
from cabotapp.views import (ServiceListView, ServiceDetailView,
    ServiceUpdateView, ServiceCreateView, ServiceDeleteView,
    UserProfileUpdateView, ShiftListView, subscriptions)
from django.contrib import admin
from django.views.generic.base import RedirectView
from django.contrib.auth.views import login, logout, password_reset, password_reset_done, password_reset_confirm
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', view=RedirectView.as_view(url='services/', permanent=False), name='dashboard'),
    url(r'^subscriptions/', view=subscriptions, name='subscriptions'),
    url(r'^accounts/login/', view=login, name='login'),
    url(r'^accounts/logout/', view=logout, name='logout'),
    url(r'^accounts/password-reset/', view=password_reset, name='password-reset'),
    url(r'^accounts/password-reset-done/', view=password_reset_done, name='password-reset-done'),
    url(r'^accounts/password-reset-confirm/', view=password_reset_confirm, name='password-reset-confirm'),
    url(r'^status/', view=checks_run_recently, name='system-status'),

    url(r'^services/', view=ServiceListView.as_view(), name='services'),
    url(r'^service/create/', view=ServiceCreateView.as_view(), name='create-service'),
    url(r'^service/update/(?P<pk>\d+)/', view=ServiceUpdateView.as_view(), name='update-service'),
    url(r'^service/delete/(?P<pk>\d+)/', view=ServiceDeleteView.as_view(), name='delete-service'),
    url(r'^service/(?P<pk>\d+)/', view=ServiceDetailView.as_view(), name='service'),
    url(r'^service/run_service_update/(?P<pk>\d+)/', view=update_service, name='run-service-update'),

    url(r'^checks/', view=StatusCheckListView.as_view(), name='checks'),
    url(r'^check/run/(?P<pk>\d+)/', view=run_status_check, name='run-check'),
    url(r'^check/delete/(?P<pk>\d+)/', view=StatusCheckDeleteView.as_view(), name='delete-check'),
    url(r'^check/(?P<pk>\d+)/', view=StatusCheckDetailView.as_view(), name='check'),

    url(r'^graphitecheck/create/', view=GraphiteCheckCreateView.as_view(), name='create-check'),
    url(r'^graphitecheck/update/(?P<pk>\d+)/', view=GraphiteCheckUpdateView.as_view(), name='update-check'),
    url(r'^httpcheck/create/', view=HttpCheckCreateView.as_view(), name='create-http-check'),
    url(r'^httpcheck/update/(?P<pk>\d+)/', view=HttpCheckUpdateView.as_view(), name='update-http-check'),
    url(r'^jenkins_check/create/', view=JenkinsCheckCreateView.as_view(), name='create-jenkins-check'),
    url(r'^jenkins_check/update/(?P<pk>\d+)/', view=JenkinsCheckUpdateView.as_view(), name='update-jenkins-check'),

    url(r'^result/(?P<service_id>\d+)/twiml_callback/', view=twiml_callback, name='twiml-callback'),
    url(r'^result/(?P<pk>\d+)/', view=StatusCheckResultDetailView.as_view(), name='result'),

    url(r'^shifts/', view=ShiftListView.as_view(), name='shifts'),

    url(r'^graphite/', view=graphite_api_data, name='graphite-data'),

    url(r'^user/(?P<pk>\d+)/profile/', view=UserProfileUpdateView.as_view(), name='user-profile'),
    url(r'^admin/', include(admin.site.urls)),
)
