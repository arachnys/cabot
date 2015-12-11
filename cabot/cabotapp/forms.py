from django import forms

class HostSearchForm(forms.Form):
    name = forms.CharField(required=False)

