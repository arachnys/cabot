import json

from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.views.generic import UpdateView, CreateView
from cabot.cabotapp.views import LoginRequiredMixin
from cabot.metricsapp.api import get_es_status_check_fields, get_status_check_fields
from cabot.metricsapp.forms import GrafanaElasticsearchStatusCheckForm, GrafanaElasticsearchStatusCheckUpdateForm
from cabot.metricsapp.models import ElasticsearchStatusCheck, GrafanaDataSource
from cabot.metricsapp.models.grafana import build_grafana_panel_from_session, set_grafana_panel_from_session


class GrafanaElasticsearchStatusCheckCreateView(LoginRequiredMixin, CreateView):
    model = ElasticsearchStatusCheck
    form_class = GrafanaElasticsearchStatusCheckForm
    template_name = 'metricsapp/grafana_create.html'

    def get_form_kwargs(self):
        kwargs = super(GrafanaElasticsearchStatusCheckCreateView, self).get_form_kwargs()

        request = self.request
        dashboard_info = request.session['dashboard_info']
        panel_info = request.session['panel_info']
        series = request.session['series']
        templating_dict = request.session['templating_dict']
        grafana_panel = build_grafana_panel_from_session(request.session)
        instance_id = request.session['instance_id']
        grafana_data_source = GrafanaDataSource.objects.get(
            grafana_source_name=request.session['datasource'],
            grafana_instance_id=instance_id
        )

        kwargs.update({
            'fields': get_status_check_fields(dashboard_info, panel_info, grafana_data_source,
                                              templating_dict, grafana_panel, request.user),
            'es_fields': get_es_status_check_fields(dashboard_info, panel_info, series),
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(GrafanaElasticsearchStatusCheckCreateView, self).get_context_data(**kwargs)
        context.update({
            'check_type': 'Elasticsearch',
            'panel_url': kwargs['form'].grafana_panel.panel_url
        })
        return context

    def get_success_url(self):
        return reverse('check', kwargs={'pk': self.object.id})

    def form_valid(self, form):
        response = super(GrafanaElasticsearchStatusCheckCreateView, self).form_valid(form)
        return response


class GrafanaElasticsearchStatusCheckUpdateView(LoginRequiredMixin, UpdateView):
    model = ElasticsearchStatusCheck
    form_class = GrafanaElasticsearchStatusCheckUpdateForm
    template_name = 'metricsapp/grafana_create.html'

    # note - this view also updates self.object.grafana_panel (via ElasticsearchStatusCheckUpdateForm)

    def get_success_url(self):
        return reverse('check', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        # review changed fields before saving changes
        # skip_review gets set by a manually added hidden checkbox input in grafana_preview_changes.html
        # (note that it is NOT part of GrafanaElasticsearchStatusCheckUpdateForm)
        if not self.request.POST.get('skip_review'):
            # create a form with the original data so we can easily render old fields in the preview_changes template
            original_form = self.form_class(initial=form.initial, instance=self.object)

            changed = [(field, original_form[field.name]) for field in form
                       if field.name in form.changed_data]

            context = {'form': form, 'changed_fields': changed}
            context.update(self.get_context_data())
            return render(self.request, 'metricsapp/grafana_preview_changes.html', context)

        # else preview accepted, continue as usual
        return super(GrafanaElasticsearchStatusCheckUpdateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(GrafanaElasticsearchStatusCheckUpdateView, self).get_context_data(**kwargs)
        if self.object.grafana_panel is not None:
            context['panel_url'] = self.object.grafana_panel.panel_url
        return context


class GrafanaElasticsearchStatusCheckRefreshView(GrafanaElasticsearchStatusCheckUpdateView):
    """
    Variant of CheckUpdateView that pre-fills the form with the latest values from Grafana.
    Note this requires the session vars by earlier Views in the "create Grafana check" flow to work
    (GrafanaDashboardSelectView, etc).
    """
    def get_form_kwargs(self):
        """Add kwargs['data'] and fill it with the latest values from Grafana"""
        kwargs = super(GrafanaElasticsearchStatusCheckRefreshView, self).get_form_kwargs()

        if self.request.method == 'GET':
            # kwargs['data'] will be the data in the form presented to the user
            # note we don't use kwargs['initial'] or override get_initial() here because we want to use form.has_changed
            # later for the preview
            kwargs['data'] = {}

            # since we are specifying the form data (in order to update values with the latest from Grafana),
            # we must set all the values or anything we omit will have the default form.widget value
            # we do this by creating a form and copying the values from it
            base_form = self.get_form_class()(instance=self.object)
            for field_name in base_form.fields:
                kwargs['data'][field_name] = base_form[field_name].value()

            # build fields which will have the latest data from Grafana
            request = self.request
            dashboard_info = request.session['dashboard_info']
            panel_info = request.session['panel_info']
            series = request.session['series']
            templating_dict = request.session['templating_dict']
            grafana_panel = build_grafana_panel_from_session(request.session)
            grafana_data_source = GrafanaDataSource.objects.get(
                grafana_source_name=request.session['datasource'],
                grafana_instance_id=request.session['instance_id']
            )

            fields = get_status_check_fields(dashboard_info, panel_info, grafana_data_source, templating_dict,
                                             grafana_panel)
            fields.update(get_es_status_check_fields(dashboard_info, panel_info, series))

            # convert the queries dict to a json string so we can render it
            fields['queries'] = json.dumps(fields['queries'])

            kwargs['data'].update(fields)

        # either way, make sure we build an updated GrafanaPanel, since that was finalized in the previous steps
        # this doesn't touch the DB yet
        set_grafana_panel_from_session(self.object.grafana_panel, self.request.session)

        return kwargs
