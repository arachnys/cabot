from cabot.cabotapp.views import SymmetricalForm
from cabot.cabotapp.models import Service, Instance
from django import forms

base_widgets = {
    'name': forms.TextInput(attrs={
        'style': 'width:30%',
    }),
    'importance': forms.RadioSelect(),
}

class StatusCheckForm(SymmetricalForm):

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

    widgets = dict(**base_widgets)
