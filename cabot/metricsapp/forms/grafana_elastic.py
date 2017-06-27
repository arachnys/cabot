from django import forms
import json
from cabot.metricsapp.api import adjust_time_range
from .grafana import GrafanaStatusCheckForm, GrafanaStatusCheckUpdateForm
from cabot.metricsapp.models import ElasticsearchStatusCheck


class GrafanaElasticsearchStatusCheckForm(GrafanaStatusCheckForm):
    class Meta:
        model = ElasticsearchStatusCheck
        fields = [
            'name',
            'queries',
            'active',
            'auto_sync',
            'check_type',
            'warning_value',
            'high_alert_importance',
            'high_alert_value',
            'time_range',
            'retries',
            'frequency',
        ]
        widgets = {
            'auto_sync': forms.CheckboxInput()
        }

    def __init__(self, *args, **kwargs):
        es_fields = kwargs.pop('es_fields')
        super(GrafanaElasticsearchStatusCheckForm, self).__init__(*args, **kwargs)

        self.fields['queries'].initial = json.dumps(es_fields['queries'])
        # Hide queries so users can't edit them
        self.fields['queries'].widget = forms.Textarea(attrs=dict(readonly='readonly',
                                                                  style='width:100%'))
        self.fields['queries'].help_text = None

    def save(self):
        """Adjust extended_bounds part of queries if the time_range is changed"""
        model = super(GrafanaElasticsearchStatusCheckForm, self).save()
        model.queries = json.dumps(adjust_time_range(json.loads(model.queries), model.time_range))
        model.save()
        return model


class GrafanaElasticsearchStatusCheckUpdateForm(GrafanaStatusCheckUpdateForm):
    class Meta:
        model = ElasticsearchStatusCheck
        fields = [
            'name',
            'queries',
            'active',
            'auto_sync',
            'check_type',
            'warning_value',
            'high_alert_importance',
            'high_alert_value',
            'time_range',
            'retries',
            'frequency',
        ]
        widgets = {
            'auto_sync': forms.CheckboxInput()
        }

    def __init__(self, *args, **kwargs):
        super(GrafanaElasticsearchStatusCheckUpdateForm, self).__init__(*args, **kwargs)
        self.fields['queries'].widget = forms.Textarea(attrs=dict(readonly='readonly',
                                                                  style='width:100%'))
        self.fields['queries'].help_text = None
