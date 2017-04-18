from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import View
from cabot.cabotapp.views import LoginRequiredMixin
from cabot.metricsapp.api import get_es_status_check_fields, get_status_check_fields
from cabot.metricsapp.forms import GrafanaElasticsearchStatusCheckForm


class GrafanaElasticsearchStatusCheckCreateView(LoginRequiredMixin, View):
    form_class = GrafanaElasticsearchStatusCheckForm
    template_name = 'metricsapp/grafana_create.html'

    def get(self, request, *args,  **kwargs):
        dashboard_info = request.session['dashboard_info']
        panel_info = request.session['panel_info']
        instance_id = request.session['instance_id']
        series = request.session['series']
        datasource = request.session['datasource']
        templating_dict = request.session['templating_dict']

        form = self.form_class(fields=get_status_check_fields(dashboard_info, panel_info, instance_id,
                                                              datasource, templating_dict),
                               es_fields=get_es_status_check_fields(dashboard_info, panel_info, series))

        return render(request, self.template_name, {'form': form, 'check_type': 'Elasticsearch'})

    def post(self, request, *args, **kwargs):
        dashboard_info = request.session['dashboard_info']
        panel_info = request.session['panel_info']
        instance_id = request.session['instance_id']
        series = request.session['series']
        datasource = request.session['datasource']
        templating_dict = request.session['templating_dict']

        form = self.form_class(request.POST,
                               fields=get_status_check_fields(dashboard_info, panel_info, instance_id,
                                                              datasource, templating_dict),
                               es_fields=get_es_status_check_fields(dashboard_info, panel_info, series))

        if form.is_valid() and not form.errors:
            check = form.save()
            return HttpResponseRedirect(reverse('check', kwargs={'pk': check.id}))

        return render(request, self.template_name, {'form': form, 'check_type': 'Elasticsearch'})
