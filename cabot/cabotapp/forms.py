from django import forms
from django.forms import widgets
from cabot.cabotapp.models import (Instance, Service)
from cabot.cabotapp import models as cabot_models

class StatusCheckForm(forms.ModelForm):
    class Meta:
        model = cabot_models.StatusCheck
        fields = ('name', 'frequency', 'importance', 'active',
                'debounce')

	widgets = {
	    'name': forms.TextInput(attrs={
		'style': 'width:30%',
	    }),
	    'importance': forms.RadioSelect(),
	}
	
    symmetrical_fields = ('service_set', 'instance_set')

    service_set = forms.ModelMultipleChoiceField(
        queryset=Service.objects.all(),
        required=False,
        help_text='Link to service(s).',
        widget=forms.SelectMultiple(
            attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            },
        )
    )

    instance_set = forms.ModelMultipleChoiceField(
        queryset=Instance.objects.all(),
        required=False,
        help_text='Link to instance(s).',
        widget=forms.SelectMultiple(
            attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            },
        )
    )

    def __init__(self, *args, **kwargs):
        super(StatusCheckForm, self).__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            for field in self.symmetrical_fields:
                self.fields[field].initial = getattr(
                    self.instance, field).all()
	    for field in self.get_distinct_field_names():
	    	self.fields[field].initial = self.instance.get_variable(field)

    def _save_m2m(self):
        # Save m2m relationships
        ret = super(StatusCheckForm, self)._save_m2m()

        # Save symmetrical fields
        for field in self.symmetrical_fields:
            setattr(self.instance, field, self.cleaned_data[field])

        # Save distinct variables
        for field in self.get_distinct_field_names():
            self.instance.set_variable(field, self.cleaned_data[field])
        
        return ret

    def get_distinct_field_names(self):
    	fields = []
	for field in iter(self.fields):
	    if field not in StatusCheckForm().fields:
	    	fields.append(field)
	return fields

