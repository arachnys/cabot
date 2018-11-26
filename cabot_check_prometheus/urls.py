from django.conf.urls import url

from .views import (PrometheusCheckCreateView, PrometheusCheckUpdateView,
                    duplicate_check)

urlpatterns = [

    url(r'^prometheuscheck/create/',
        view=PrometheusCheckCreateView.as_view(),
        name='create-prometheus-check'),

    url(r'^prometheuscheck/update/(?P<pk>\d+)/',
        view=PrometheusCheckUpdateView.as_view(),
        name='update-prometheus-check'),

    url(r'^prometheuscheck/duplicate/(?P<pk>\d+)/',
        view=duplicate_check,
        name='duplicate-prometheus-check')

]
