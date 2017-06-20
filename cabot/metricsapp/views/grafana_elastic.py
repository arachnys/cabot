from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import View, UpdateView
from cabot.cabotapp.views import LoginRequiredMixin
from cabot.metricsapp.api import get_es_status_check_fields, get_status_check_fields, get_panel_url
from cabot.metricsapp.forms import GrafanaElasticsearchStatusCheckForm, GrafanaElasticsearchStatusCheckUpdateForm
from cabot.metricsapp.models import GrafanaInstance, ElasticsearchStatusCheck, GrafanaDataSource


class GrafanaElasticsearchStatusCheckCreateView(LoginRequiredMixin, View):
    form_class = GrafanaElasticsearchStatusCheckForm
    template_name = 'metricsapp/grafana_create.html'

    def get(self, request, *args,  **kwargs):
        dashboard_info = request.session['dashboard_info']
        panel_info = request.session['panel_info']
        series = request.session['series']
        templating_dict = request.session['templating_dict']
        grafana_panel = request.session['grafana_panel']
        instance_id = request.session['instance_id']
        grafana_data_source = GrafanaDataSource.objects.get(
            grafana_source_name=request.session['datasource'],
            grafana_instance_id=instance_id
        )

        form = self.form_class(fields=get_status_check_fields(dashboard_info, panel_info, grafana_data_source,
                                                              templating_dict, grafana_panel),
                               es_fields=get_es_status_check_fields(dashboard_info, panel_info, series))

        panel_url = get_panel_url(GrafanaInstance.objects.get(id=instance_id).url,
                                  request.session['dashboard_uri'],
                                  request.session['panel_id'],
                                  templating_dict)
        return render(request, self.template_name, {'form': form, 'check_type': 'Elasticsearch',
                                                    'panel_url': panel_url})

    def post(self, request, *args, **kwargs):
        dashboard_info = request.session['dashboard_info']
        panel_info = request.session['panel_info']
        series = request.session['series']
        templating_dict = request.session['templating_dict']
        grafana_panel = request.session['grafana_panel']
        instance_id = request.session['instance_id']
        grafana_data_source = GrafanaDataSource.objects.get(
            grafana_source_name=request.session['datasource'],
            grafana_instance_id=instance_id
        )

        form = self.form_class(request.POST,
                               fields=get_status_check_fields(dashboard_info, panel_info, grafana_data_source,
                                                              templating_dict, grafana_panel),
                               es_fields=get_es_status_check_fields(dashboard_info, panel_info, series))

        if form.is_valid() and not form.errors:
            check = form.save()
            return HttpResponseRedirect(reverse('check', kwargs={'pk': check.id}))

        panel_url = get_panel_url(GrafanaInstance.objects.get(id=instance_id).url,
                                  request.session['dashboard_uri'],
                                  request.session['panel_id'],
                                  templating_dict)
        return render(request, self.template_name, {'form': form, 'check_type': 'Elasticsearch',
                                                    'panel_url': panel_url})


class GrafanaElasticsearchStatusCheckUpdateView(LoginRequiredMixin, UpdateView):
    model = ElasticsearchStatusCheck
    form_class = GrafanaElasticsearchStatusCheckUpdateForm
    template_name = 'metricsapp/grafana_create.html'

    def get_success_url(self):
        return reverse('check', kwargs={'pk': self.object.id})


class GrafanaElasticsearchStatusCheckRefreshView(GrafanaElasticsearchStatusCheckUpdateView):
    def get(self, request, *args, **kwargs):
        """Alter the check based on the new info from the dashboard before letting the user update"""
        dashboard_info = request.session['dashboard_info']
        panel_info = request.session['panel_info']
        series = request.session['series']
        templating_dict = request.session['templating_dict']
        grafana_panel = request.session['grafana_panel']
        grafana_data_source = GrafanaDataSource.objects.get(
            grafana_source_name=request.session['datasource'],
            grafana_instance_id=request.session['instance_id']
        )

        fields = get_status_check_fields(dashboard_info, panel_info, grafana_data_source, templating_dict,
                                         grafana_panel)
        fields.update(get_es_status_check_fields(dashboard_info, panel_info, series))

        check = ElasticsearchStatusCheck.objects.get(id=kwargs['pk'])
        check.set_fields_from_grafana(fields)

        return super(GrafanaElasticsearchStatusCheckRefreshView, self).get(self, request, *args, **kwargs)
