import json
import re
from datetime import datetime, timedelta, date
from itertools import groupby, dropwhile, izip_longest

import requests
from cabot.cabotapp import alert
from dateutil.relativedelta import relativedelta
from django import forms
from django.conf import settings
from models import (StatusCheck, StatusCheckResult, UserProfile, Service,
    Instance, Shift, get_duty_officers, StatusCheckVariable)
from tasks import run_status_check as _run_status_check
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import (
    DetailView, CreateView, UpdateView, ListView, DeleteView, TemplateView, FormView, View)
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.timezone import utc
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError

from cabot.plugins.models import PluginModel, AlertPluginModel, StatusCheckPluginModel, AlertPluginUserData, FailedImport
from django.forms.models import (inlineformset_factory, modelformset_factory)
from django import shortcuts
from braces.views import LoginRequiredMixin, SuperuserRequiredMixin

from itertools import groupby, dropwhile, izip_longest
import requests
import json
import re

from logging import getLogger
logger = getLogger(__name__)


@login_required
def subscriptions(request):
    """ Simple list of all checks """
    t = loader.get_template('cabotapp/subscriptions.html')
    services = Service.objects.all()
    users = User.objects.filter(is_active=True)
    c = RequestContext(request, {
        'services': services,
        'users': users,
        'duty_officers': get_duty_officers(),
    })
    return HttpResponse(t.render(c))


@login_required
def run_status_check(request, pk):
    """Runs a specific check"""
    _run_status_check(check_or_id=pk)
    return HttpResponseRedirect(reverse('check', kwargs={'pk': pk}))

def duplicate_instance(request, pk):
    instance = Instance.objects.get(pk=pk)
    new_instance = instance.duplicate()
    return HttpResponseRedirect(reverse('update-instance', kwargs={'pk': new_instance}))

def duplicate_check(request, pk):
    check = StatusCheck.objects.get(pk=pk)
    new_check = check.duplicate(check.instance_set.all(), check.service_set.all())
    return HttpResponseRedirect(reverse('update-check', kwargs={'pk': new_check}))
class StatusCheckResultDetailView(LoginRequiredMixin, DetailView):
    model = StatusCheckResult
    context_object_name = 'result'


class SymmetricalForm(forms.ModelForm):
    symmetrical_fields = ()  # Iterable of 2-tuples (field, model)

    def __init__(self, *args, **kwargs):
        super(SymmetricalForm, self).__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            for field in self.symmetrical_fields:
                self.fields[field].initial = getattr(
                    self.instance, field).all()

    def save(self, commit=True):
        instance = super(SymmetricalForm, self).save(commit=False)
        if commit:
            instance.save()
        if instance.pk:
            for field in self.symmetrical_fields:
                setattr(instance, field, self.cleaned_data[field])
            self.save_m2m()
        return instance


base_widgets = {
    'name': forms.TextInput(attrs={
        'style': 'width:30%',
    }),
    'importance': forms.RadioSelect(),
}


class InstanceForm(SymmetricalForm):
    symmetrical_fields = ('service_set',)
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

    class Meta:
        model = Instance
        template_name = 'instance_form.html'
        fields = (
            'name',
            'address',
            'users_to_notify',
            'status_checks',
            'service_set',
        )
        widgets = {
            'name': forms.TextInput(attrs={'style': 'width: 30%;'}),
            'address': forms.TextInput(attrs={'style': 'width: 70%;'}),
            'status_checks': forms.SelectMultiple(attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            }),
            'service_set': forms.SelectMultiple(attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            }),
            'alerts': forms.SelectMultiple(attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            }),
            'users_to_notify': forms.CheckboxSelectMultiple(),
            'hackpad_id': forms.TextInput(attrs={'style': 'width:30%;'}),
        }

    def __init__(self, *args, **kwargs):
        ret = super(InstanceForm, self).__init__(*args, **kwargs)
        self.fields['users_to_notify'].queryset = User.objects.filter(
            is_active=True).order_by('first_name', 'last_name')
        return ret


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        template_name = 'service_form.html'
        fields = (
            'name',
            'url',
            'users_to_notify',
            'status_checks',
            'instances',
            'alerts',
            'alerts_enabled',
            'hackpad_id',
        )
        widgets = {
            'name': forms.TextInput(attrs={'style': 'width: 30%;'}),
            'url': forms.TextInput(attrs={'style': 'width: 70%;'}),
            'status_checks': forms.SelectMultiple(attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            }),
            'instances': forms.SelectMultiple(attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            }),
            'alerts': forms.SelectMultiple(attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            }),
            'users_to_notify': forms.CheckboxSelectMultiple(),
            'hackpad_id': forms.TextInput(attrs={'style': 'width:30%;'}),
        }

    def __init__(self, *args, **kwargs):
        ret = super(ServiceForm, self).__init__(*args, **kwargs)
        self.fields['users_to_notify'].queryset = User.objects.filter(
            is_active=True).order_by('first_name', 'last_name')
        return ret

    def clean_hackpad_id(self):
        value = self.cleaned_data['hackpad_id']
        if not value:
            return ''
        for pattern in settings.RECOVERY_SNIPPETS_WHITELIST:
            if re.match(pattern, value):
                return value
        raise ValidationError('Please specify a valid JS snippet link')


class StatusCheckReportForm(forms.Form):
    service = forms.ModelChoiceField(
        queryset=Service.objects.all(),
        widget=forms.HiddenInput
    )
    checks = forms.ModelMultipleChoiceField(
        queryset=StatusCheck.objects.all(),
        widget=forms.SelectMultiple(
            attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            },
        )
    )
    date_from = forms.DateField(label='From', widget=forms.DateInput(attrs={'class': 'datepicker'}))
    date_to = forms.DateField(label='To', widget=forms.DateInput(attrs={'class': 'datepicker'}))

    def get_report(self):
        checks = self.cleaned_data['checks']
        now = timezone.now()
        for check in checks:
            # Group results of the check by status (failed alternating with succeeded),
            # take time of the first one in each group (starting from a failed group),
            # split them into pairs and form the list of problems.
            results = check.statuscheckresult_set.filter(
                time__gte=self.cleaned_data['date_from'],
                time__lt=self.cleaned_data['date_to'] + timedelta(days=1)
            ).order_by('time')
            groups = dropwhile(lambda item: item[0], groupby(results, key=lambda r: r.succeeded))
            times = [next(group).time for succeeded, group in groups]
            pairs = izip_longest(*([iter(times)] * 2))
            check.problems = [(start, end, (end or now) - start) for start, end in pairs]
            if results:
                check.success_rate = results.filter(succeeded=True).count() / float(len(results)) * 100
        return checks

class StatusCheckViewMixin(LoginRequiredMixin):
    template_name = 'cabotapp/statuscheck_form.html'
    model = StatusCheck

    # Merge the forms. CheckConfigForm has special methods for handling this.
    def get_form_class(self):
        from .forms import StatusCheckForm
        class FormClass(StatusCheckForm, self.get_status_check_plugin().config_form):
            pass
        return FormClass

    def get_status_check_plugin(self):
        plugin_pk = self.request.GET['type']
        return StatusCheckPluginModel.objects.get(pk=plugin_pk)

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.check_plugin = self.get_status_check_plugin()
        instance.save()
        form.save_m2m()
        return super(StatusCheckViewMixin, self).form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super(StatusCheckViewMixin, self).get_context_data(**kwargs)
        context['check_plugin'] = self.get_status_check_plugin()
        return context

class StatusCheckCreateView(StatusCheckViewMixin, CreateView):
    pass


class StatusCheckUpdateView(StatusCheckViewMixin, UpdateView):
    def get_status_check_plugin(self):
        instance = StatusCheck.objects.get(pk=self.kwargs['pk'])
        return instance.check_plugin

class StatusCheckListView(LoginRequiredMixin, ListView):
    model = StatusCheck
    context_object_name = 'checks'

    def get_queryset(self):
        return StatusCheck.objects.all().order_by('name').prefetch_related('service_set', 'instance_set')


class StatusCheckDeleteView(LoginRequiredMixin, DeleteView):
    model = StatusCheck
    success_url = reverse_lazy('checks')
    context_object_name = 'check'
    template_name = 'cabotapp/statuscheck_confirm_delete.html'


class StatusCheckDetailView(LoginRequiredMixin, DetailView):
    model = StatusCheck
    context_object_name = 'check'
    template_name = 'cabotapp/statuscheck_detail.html'

    def render_to_response(self, context, *args, **kwargs):
        if context is None:
            context = {}
        context['checkresults'] = self.object.statuscheckresult_set.order_by(
            '-time_complete')[:100]
        return super(StatusCheckDetailView, self).render_to_response(context, *args, **kwargs)

class UpdateUserView(LoginRequiredMixin, UpdateView):
    model = User
    fields = ['first_name', 'last_name', 'email', 'is_active']
    template_name = 'cabotapp/alertpluginuserdata_form.html'

    def get_object(self):
        return User.objects.get(pk=self.kwargs['pk'])

    # Add the list of plugins to the template context to display in the sidebar
    def get_context_data(self, **kwargs):
        context = super(UpdateUserView, self).get_context_data(**kwargs)
        alert_plugins = [p for p in AlertPluginModel.objects.all() if p.plugin_class and p.plugin_class.user_config_form]
        context['alert_plugins'] = alert_plugins
        context['form_title'] = 'User Profile'
        context['user_being_updated'] = self.object

        return context

    def get_success_url(self):
        return reverse('update-user', kwargs={'pk': self.kwargs['pk']})


class UpdateUserAlertPluginDataView(LoginRequiredMixin, View):
    template = loader.get_template('cabotapp/alertpluginuserdata_form.html')

    def get(self, request, pk, alert_plugin_pk):
        user = User.objects.get(pk=pk)
        plugin = AlertPluginModel.objects.get(pk=alert_plugin_pk)
        initial = {}
        for ud in AlertPluginUserData.objects.filter(user=user, plugin=plugin):
            initial[ud.key] = ud.value
        
        form = plugin.plugin_class.user_config_form(initial=initial)
        alert_plugins = [p for p in AlertPluginModel.objects.all() if p.plugin_class and p.plugin_class.user_config_form]

        c = RequestContext(request, {
            'form': form,
            'alert_plugins': alert_plugins,
            'form_title': plugin.name + ' Settings',
            'user_being_updated': user,
        })

        return HttpResponse(self.template.render(c))

    def post(self, request, pk, alert_plugin_pk):
        user = User.objects.get(pk=pk)
        plugin = PluginModel.objects.get(pk=alert_plugin_pk)

        form = plugin.plugin_class.user_config_form(request.POST)

        if form.is_valid():
            for key in form.cleaned_data:
                ud, created = AlertPluginUserData.objects.get_or_create(
                        user=user,
                        plugin=plugin,
                        key=key)
                ud.value = form.cleaned_data[key]
                ud.save()

        return HttpResponseRedirect(reverse('update-user-userdata', kwargs={'pk': pk, 'alert_plugin_pk': alert_plugin_pk}))


class InstanceListView(LoginRequiredMixin, ListView):
    model = Instance
    context_object_name = 'instances'

    def get_queryset(self):
        return Instance.objects.all().order_by('name').prefetch_related('status_checks')


class ServiceListView(LoginRequiredMixin, ListView):
    model = Service
    context_object_name = 'services'

    def get_queryset(self):
        return Service.objects.all().order_by('name').prefetch_related('status_checks')


class InstanceDetailView(LoginRequiredMixin, DetailView):
    model = Instance
    context_object_name = 'instance'

    def get_context_data(self, **kwargs):
        context = super(InstanceDetailView, self).get_context_data(**kwargs)
        date_from = date.today() - relativedelta(day=1)
        context['report_form'] = StatusCheckReportForm(initial={
            'checks': self.object.status_checks.all(),
            'service': self.object,
            'date_from': date_from,
            'date_to': date_from + relativedelta(months=1) - relativedelta(days=1)
        })
        return context


class ServiceDetailView(LoginRequiredMixin, DetailView):
    model = Service
    context_object_name = 'service'

    def get_context_data(self, **kwargs):
        context = super(ServiceDetailView, self).get_context_data(**kwargs)
        date_from = date.today() - relativedelta(day=1)
        context['report_form'] = StatusCheckReportForm(initial={
            'alerts': self.object.alerts.all(),
            'checks': self.object.status_checks.all(),
            'service': self.object,
            'date_from': date_from,
            'date_to': date_from + relativedelta(months=1) - relativedelta(days=1)
        })
        return context


class InstanceCreateView(LoginRequiredMixin, CreateView):
    model = Instance
    form_class = InstanceForm

    def form_valid(self, form):
        ret = super(InstanceCreateView, self).form_valid(form)
        if StatusCheckPluginModel.objects.filter(slug='cabot_check_icmp').exists():
            self.generate_default_ping_check(self.object)
        return ret

    def generate_default_ping_check(self, obj):
        icmp_check_plugin = StatusCheckPluginModel.objects.get(slug='cabot_check_icmp')

        new_check = StatusCheck.objects.create(
            name = 'Default Ping Check for {}'.format(obj.name),
            check_plugin = icmp_check_plugin,
            frequency = 5,
            importance = Service.ERROR_STATUS,
            debounce = 0,
            created_by = None
            )

        obj.status_checks.add(new_check)

    def get_initial(self):
        if self.initial:
            initial = self.initial
        else:
            initial = {}
        service_id = self.request.GET.get('service')

        if service_id:
            try:
                service = Service.objects.get(id=service_id)
                initial['service_set'] = [service]
            except Service.DoesNotExist:
                pass

        return initial


@login_required
def acknowledge_alert(request, pk):
    service = Service.objects.get(pk=pk)
    service.acknowledge_alert(user=request.user)
    return HttpResponseRedirect(reverse('service', kwargs={'pk': pk}))


@login_required
def remove_acknowledgement(request, pk):
    service = Service.objects.get(pk=pk)
    service.remove_acknowledgement(user=request.user)
    return HttpResponseRedirect(reverse('service', kwargs={'pk': pk}))


class ServiceCreateView(LoginRequiredMixin, CreateView):
    model = Service
    form_class = ServiceForm

    def get_success_url(self):
        return reverse('service', kwargs={'pk': self.object.id})


class InstanceUpdateView(LoginRequiredMixin, UpdateView):
    model = Instance
    form_class = InstanceForm

    def get_success_url(self):
        return reverse('instance', kwargs={'pk': self.object.id})


class ServiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Service
    form_class = ServiceForm

    def get_success_url(self):
        return reverse('service', kwargs={'pk': self.object.id})


class ServiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Service
    success_url = reverse_lazy('services')
    context_object_name = 'service'
    template_name = 'cabotapp/service_confirm_delete.html'


class InstanceDeleteView(LoginRequiredMixin, DeleteView):
    model = Instance
    success_url = reverse_lazy('instances')
    context_object_name = 'instance'
    template_name = 'cabotapp/instance_confirm_delete.html'


class ShiftListView(LoginRequiredMixin, ListView):
    model = Shift
    context_object_name = 'shifts'

    def get_queryset(self):
        return Shift.objects.filter(
            end__gt=datetime.utcnow().replace(tzinfo=utc),
            deleted=False).order_by('start')


class StatusCheckReportView(LoginRequiredMixin, TemplateView):
    template_name = 'cabotapp/statuscheck_report.html'

    def get_context_data(self, **kwargs):
        form = StatusCheckReportForm(self.request.GET)
        if form.is_valid():
            return {'checks': form.get_report(), 'service': form.cleaned_data['service']}

class PluginListView(LoginRequiredMixin, SuperuserRequiredMixin, ListView):
    model = PluginModel
    template_name = 'cabotapp/plugins_list.html'

    def get_context_data(self, **kwargs):
        context = super(PluginListView, self).get_context_data(**kwargs)
        context['failed_imports'] = FailedImport.objects.all()
        return context

class TestAlertPluginForm(forms.Form):
    service = forms.ModelChoiceField(
        queryset=Service.objects.all(),
        required=True,
    )
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=True,
        widget=forms.SelectMultiple(
            attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            },
        )
    )


class PluginDetailView(LoginRequiredMixin, SuperuserRequiredMixin, DetailView):
    model = PluginModel
    context_object_name = 'plugin'
    template_name = 'cabotapp/plugins_detail.html'

    def get_context_data(self, **kwargs):
        context = super(PluginDetailView, self).get_context_data(**kwargs)
        context['form'] = TestAlertPluginForm()
        context['isAlertPlugin'] = isinstance(self.object, AlertPluginModel)
        context['isStatusCheckPlugin'] = isinstance(self.object, StatusCheckPluginModel)
        return context

    def post(self, request, pk):
        form = TestAlertPluginForm(request.POST)
        if form.is_valid():
            plugin = AlertPluginModel.objects.get(pk=pk)
            plugin.send_alert(
                service=form.cleaned_data['service'],
                users=form.cleaned_data['users'],
                duty_officers=[]
                )
        return HttpResponseRedirect(reverse('plugin', kwargs={'pk': pk}))


# Misc JSON api and other stuff


def checks_run_recently(request):
    """
    Checks whether or not stuff is running by looking to see if checks have run in last 10 mins
    """
    ten_mins = datetime.utcnow().replace(tzinfo=utc) - timedelta(minutes=10)
    most_recent = StatusCheckResult.objects.filter(time_complete__gte=ten_mins)
    if most_recent.exists():
        return HttpResponse('Checks running')
    return HttpResponse('Checks not running')


def jsonify(d):
    return HttpResponse(json.dumps(d), content_type='application/json')

