import json
import re
from datetime import date, datetime, timedelta
from itertools import dropwhile, groupby, izip_longest

import requests
from alert import AlertPlugin, AlertPluginUserData
from cabot.cabotapp import alert
from cabot.cabotapp.utils import cabot_needs_setup
from dateutil.relativedelta import relativedelta
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models.functions import Lower
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.template import RequestContext, loader
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.timezone import utc
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView, View)
from models import (GraphiteStatusCheck, HttpStatusCheck, ICMPStatusCheck,
                    Instance, JenkinsStatusCheck, Service, Shift, StatusCheck,
                    StatusCheckResult, UserProfile, get_custom_check_plugins,
                    get_duty_officers)
from rest_framework.views import APIView
from rest_framework.response import Response
from tasks import run_status_check as _run_status_check

from .graphite import get_data, get_matching_metrics


class LoginRequiredMixin(object):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


@login_required
def subscriptions(request):
    """ Simple list of all checks """
    services = Service.objects.all()
    users = User.objects.filter(is_active=True)

    return render(request, 'cabotapp/subscriptions.html', {
        'services': services,
        'users': users,
        'duty_officers': get_duty_officers(),
        'custom_check_types': get_custom_check_plugins(),
    })


@login_required
def run_status_check(request, pk):
    """Runs a specific check"""
    _run_status_check(check_or_id=pk)
    return HttpResponseRedirect(reverse('check', kwargs={'pk': pk}))


def duplicate_icmp_check(request, pk):
    pc = StatusCheck.objects.get(pk=pk)
    npk = pc.duplicate()
    return HttpResponseRedirect(reverse('update-icmp-check', kwargs={'pk': npk}))


def duplicate_instance(request, pk):
    instance = Instance.objects.get(pk=pk)
    new_instance = instance.duplicate()
    return HttpResponseRedirect(reverse('update-instance', kwargs={'pk': new_instance}))


def duplicate_http_check(request, pk):
    pc = StatusCheck.objects.get(pk=pk)
    npk = pc.duplicate()
    return HttpResponseRedirect(reverse('update-http-check', kwargs={'pk': npk}))


def duplicate_graphite_check(request, pk):
    pc = StatusCheck.objects.get(pk=pk)
    npk = pc.duplicate()
    return HttpResponseRedirect(reverse('update-graphite-check', kwargs={'pk': npk}))


def duplicate_jenkins_check(request, pk):
    pc = StatusCheck.objects.get(pk=pk)
    npk = pc.duplicate()
    return HttpResponseRedirect(reverse('update-jenkins-check', kwargs={'pk': npk}))


class BaseCommonView(object):
    def render_to_response(self, context, *args, **kwargs):
        if context is None:
            context = {}
        context['custom_check_types'] = get_custom_check_plugins()
        return super(BaseCommonView, self).render_to_response(context, *args, **kwargs)


class CommonCreateView(BaseCommonView, CreateView):
    pass


class CommonUpdateView(BaseCommonView, UpdateView):
    pass


class CommonDeleteView(BaseCommonView, DeleteView):
    pass


class CommonDetailView(BaseCommonView, DetailView):
    pass


class CommonListView(BaseCommonView, ListView):
    pass


class StatusCheckResultDetailView(LoginRequiredMixin, CommonDetailView):
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


class GraphiteStatusCheckForm(StatusCheckForm):
    class Meta:
        model = GraphiteStatusCheck
        fields = (
            'name',
            'metric',
            'check_type',
            'value',
            'frequency',
            'active',
            'importance',
            'expected_num_hosts',
            'allowed_num_failures',
            'debounce',
        )
        widgets = dict(**base_widgets)
        widgets.update({
            'value': forms.TextInput(attrs={
                'style': 'width: 100px',
                'placeholder': 'threshold value',
            }),
            'metric': forms.TextInput(attrs={
                'style': 'width: 100%',
                'placeholder': 'graphite metric key'
            }),
            'check_type': forms.Select(attrs={
                'data-rel': 'chosen',
            })
        })


class ICMPStatusCheckForm(StatusCheckForm):
    class Meta:
        model = ICMPStatusCheck
        fields = (
            'name',
            'frequency',
            'importance',
            'active',
            'debounce',
        )
        widgets = dict(**base_widgets)


class HttpStatusCheckForm(StatusCheckForm):
    class Meta:
        model = HttpStatusCheck
        fields = (
            'name',
            'endpoint',
            'username',
            'password',
            'text_match',
            'status_code',
            'timeout',
            'verify_ssl_certificate',
            'frequency',
            'importance',
            'active',
            'debounce',
        )
        widgets = dict(**base_widgets)
        widgets.update({
            'endpoint': forms.TextInput(attrs={
                'style': 'width: 100%',
                'placeholder': 'https://www.example.org/',
            }),
            'username': forms.TextInput(attrs={
                'style': 'width: 30%',
            }),
            'password': forms.PasswordInput(attrs={
                'style': 'width: 30%',
                # Prevent auto-fill with saved Cabot log-in credentials:
                'autocomplete': 'new-password',
            }),
            'text_match': forms.TextInput(attrs={
                'style': 'width: 100%',
                'placeholder': '[Aa]rachnys\s+[Rr]ules',
            }),
            'status_code': forms.TextInput(attrs={
                'style': 'width: 20%',
                'placeholder': '200',
            }),
        })

    def clean_password(self):
        new_password_value = self.cleaned_data['password']
        if new_password_value == '':
            new_password_value = self.initial.get('password')
        return new_password_value


class JenkinsStatusCheckForm(StatusCheckForm):
    class Meta:
        model = JenkinsStatusCheck
        fields = (
            'name',
            'importance',
            'debounce',
            'max_queued_build_time',
            'jenkins_config',
        )
        widgets = dict(**base_widgets)


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
            'name': forms.TextInput(attrs={'style': 'width: 70%;'}),
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
            'users_to_notify': forms.SelectMultiple(attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            }),
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
            'runbook_link',
            'is_public'
        )
        widgets = {
            'name': forms.TextInput(attrs={'style': 'width: 70%;'}),
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
            'users_to_notify': forms.SelectMultiple(attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            }),
            'hackpad_id': forms.TextInput(attrs={'style': 'width:70%;'}),
            'runbook_link': forms.TextInput(attrs={'style': 'width:70%;'}),
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

    def clean_runbook_link(self):
        value = self.cleaned_data['runbook_link']
        if not value:
            return ''
        try:
            URLValidator()(value)
            return value
        except ValidationError:
            raise ValidationError('Please specify a valid runbook link')

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


class CheckCreateView(LoginRequiredMixin, CommonCreateView):
    template_name = 'cabotapp/statuscheck_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super(CheckCreateView, self).form_valid(form)

    def get_initial(self):
        if self.initial:
            initial = self.initial
        else:
            initial = {}
        metric = self.request.GET.get('metric')
        if metric:
            initial['metric'] = metric
        service_id = self.request.GET.get('service')
        instance_id = self.request.GET.get('instance')

        if service_id:
            try:
                service = Service.objects.get(id=service_id)
                initial['service_set'] = [service]
            except Service.DoesNotExist:
                pass

        if instance_id:
            try:
                instance = Instance.objects.get(id=instance_id)
                initial['instance_set'] = [instance]
            except Instance.DoesNotExist:
                pass

        return initial

    def get_success_url(self):
        if self.request.GET.get('service'):
            return reverse('service', kwargs={'pk': self.request.GET.get('service')})
        if self.request.GET.get('instance'):
            return reverse('instance', kwargs={'pk': self.request.GET.get('instance')})
        return reverse('checks')


class CheckUpdateView(LoginRequiredMixin, CommonUpdateView):
    template_name = 'cabotapp/statuscheck_form.html'

    def get_success_url(self):
        return reverse('check', kwargs={'pk': self.object.id})


class ICMPCheckCreateView(CheckCreateView):
    model = ICMPStatusCheck
    form_class = ICMPStatusCheckForm


class ICMPCheckUpdateView(CheckUpdateView):
    model = ICMPStatusCheck
    form_class = ICMPStatusCheckForm


class GraphiteCheckUpdateView(CheckUpdateView):
    model = GraphiteStatusCheck
    form_class = GraphiteStatusCheckForm


class GraphiteCheckCreateView(CheckCreateView):
    model = GraphiteStatusCheck
    form_class = GraphiteStatusCheckForm


class HttpCheckCreateView(CheckCreateView):
    model = HttpStatusCheck
    form_class = HttpStatusCheckForm


class HttpCheckUpdateView(CheckUpdateView):
    model = HttpStatusCheck
    form_class = HttpStatusCheckForm


class JenkinsCheckCreateView(CheckCreateView):
    model = JenkinsStatusCheck
    form_class = JenkinsStatusCheckForm

    def form_valid(self, form):
        form.instance.frequency = 1
        return super(JenkinsCheckCreateView, self).form_valid(form)


class JenkinsCheckUpdateView(CheckUpdateView):
    model = JenkinsStatusCheck
    form_class = JenkinsStatusCheckForm

    def form_valid(self, form):
        form.instance.frequency = 1
        return super(JenkinsCheckUpdateView, self).form_valid(form)


class StatusCheckListView(LoginRequiredMixin, CommonListView):
    model = StatusCheck

    def render_to_response(self, context, *args, **kwargs):
        context = super(StatusCheckListView, self).get_context_data(**kwargs)
        if context is None:
            context = {}
        context['checks'] = StatusCheck.objects.all().order_by('name').prefetch_related('service_set', 'instance_set')
        return super(StatusCheckListView, self).render_to_response(context, *args, **kwargs)


class StatusCheckDeleteView(LoginRequiredMixin, CommonDeleteView):
    model = StatusCheck
    success_url = reverse_lazy('checks')
    context_object_name = 'check'
    template_name = 'cabotapp/statuscheck_confirm_delete.html'


class StatusCheckDetailView(LoginRequiredMixin, CommonDetailView):
    model = StatusCheck
    context_object_name = 'check'
    template_name = 'cabotapp/statuscheck_detail.html'

    def render_to_response(self, context, *args, **kwargs):
        if context is None:
            context = {}
        checkresult_list = self.object.statuscheckresult_set.order_by(
            '-time_complete').all()
        paginator = Paginator(checkresult_list, 25)

        page = self.request.GET.get('page')
        try:
            checkresults = paginator.page(page)
        except PageNotAnInteger:
            checkresults = paginator.page(1)
        except EmptyPage:
            checkresults = paginator.page(paginator.num_pages)

        context['checkresults'] = checkresults

        return super(StatusCheckDetailView, self).render_to_response(context, *args, **kwargs)


class UserProfileUpdateView(LoginRequiredMixin, View):
    model = AlertPluginUserData

    def get(self, *args, **kwargs):
        return HttpResponseRedirect(reverse('update-alert-user-data', args=(self.kwargs['pk'], u'General')))


class UserProfileUpdateAlert(LoginRequiredMixin, View):
    template = loader.get_template('cabotapp/alertpluginuserdata_form.html')
    model = AlertPluginUserData

    def get(self, request, pk, alerttype):
        try:
            profile = UserProfile.objects.get(user=pk)
        except UserProfile.DoesNotExist:
            user = User.objects.get(id=pk)
            profile = UserProfile(user=user)
            profile.save()

        profile.user_data()

        if alerttype == u'General':
            form = GeneralSettingsForm(initial={
                'first_name': profile.user.first_name,
                'last_name': profile.user.last_name,
                'email_address': profile.user.email,
                'enabled': profile.user.is_active,
            })
        else:
            plugin_userdata = self.model.objects.get(title=alerttype, user=profile)
            form_model = get_object_form(type(plugin_userdata))
            form = form_model(instance=plugin_userdata)

        return render(request, self.template.template.name, {
            'form': form,
            'alert_preferences': profile.user_data(),
            'custom_check_types': get_custom_check_plugins(),
        })

    def post(self, request, pk, alerttype):
        profile = UserProfile.objects.get(user=pk)
        success = False

        if alerttype == u'General':
            form = GeneralSettingsForm(request.POST)
            if form.is_valid():
                profile.user.first_name = form.cleaned_data['first_name']
                profile.user.last_name = form.cleaned_data['last_name']
                profile.user.is_active = form.cleaned_data['enabled']
                profile.user.email = form.cleaned_data['email_address']
                profile.user.save()

                success = True
        else:
            plugin_userdata = self.model.objects.get(title=alerttype, user=profile)
            form_model = get_object_form(type(plugin_userdata))
            form = form_model(request.POST, instance=plugin_userdata)
            if form.is_valid():
                form.save()

                success = True

        if success:
            messages.add_message(request, messages.SUCCESS, 'Updated Successfully', extra_tags='success')
        else:
            messages.add_message(request, messages.ERROR, 'Error Updating Profile', extra_tags='danger')

        return HttpResponseRedirect(reverse('update-alert-user-data', args=(self.kwargs['pk'], alerttype)))


class PluginSettingsView(LoginRequiredMixin, View):
    template = loader.get_template('cabotapp/plugin_settings_form.html')
    model = AlertPlugin

    def get(self, request, plugin_name):
        if plugin_name == u'global':
            form = CoreSettingsForm()
            alert_test_form = AlertTestForm()
        else:
            plugin = self.model.objects.get(title=plugin_name)
            form_model = get_object_form(type(plugin))
            form = form_model(instance=plugin)
            alert_test_form = AlertTestPluginForm(initial = {
                'alert_plugin': plugin
            })

        return render(request, self.template.template.name, {
            'form': form,
            'plugins': AlertPlugin.objects.all(),
            'plugin_name': plugin_name,
            'alert_test_form': alert_test_form,
            'custom_check_types': get_custom_check_plugins()
        })

    def post(self, request, plugin_name):
        if plugin_name == u'global':
            form = CoreSettingsForm(request.POST)
        else:
            plugin = self.model.objects.get(title=plugin_name)
            form_model = get_object_form(type(plugin))
            form = form_model(request.POST, instance=plugin)

        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Updated Successfully', extra_tags='success')
        else:
            messages.add_message(request, messages.ERROR, 'Error Updating Plugin', extra_tags='danger')

        return HttpResponseRedirect(reverse('plugin-settings', args=(plugin_name,)))


def get_object_form(model_type):
    class AlertPreferencesForm(forms.ModelForm):
        class Meta:
            model = model_type
            fields = '__all__'

        def is_valid(self):
            return True

    return AlertPreferencesForm


class AlertTestForm(forms.Form):
    action = reverse_lazy('alert-test')

    service = forms.ModelChoiceField(
        queryset=Service.objects.all(),
        widget=forms.Select(attrs={
            'data-rel': 'chosen',
        })
    )

    STATUS_CHOICES = (
        (Service.PASSING_STATUS, 'Passing'),
        (Service.WARNING_STATUS, 'Warning'),
        (Service.ERROR_STATUS, 'Error'),
        (Service.CRITICAL_STATUS, 'Critical'),
    )

    old_status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        initial=Service.PASSING_STATUS,
        widget=forms.Select(attrs={
            'data-rel': 'chosen',
        })
    )

    new_status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        initial=Service.ERROR_STATUS,
        widget=forms.Select(attrs={
            'data-rel': 'chosen',
        })
    )


class AlertTestPluginForm(AlertTestForm):
    action = reverse_lazy('alert-test-plugin')

    service = None
    alert_plugin = forms.ModelChoiceField(
        queryset=AlertPlugin.objects.filter(enabled=True),
        widget=forms.HiddenInput
    )


class AlertTestView(LoginRequiredMixin, View):
    def trigger_alert_to_user(self, service, user, old_status, new_status):
        """
        Clear out all service users and duty shifts, and disable all fallback users.
        Then add a single shift for this user, and add this user to users-to-notify.

        This should ensure we never alert anyone except the user triggering the alert test.
        """
        with transaction.atomic():
            sid = transaction.savepoint()
            service.update_status()
            service.status_checks.update(active=False)
            service.overall_status = new_status
            service.old_overall_status = old_status
            service.last_alert_sent = None

            check = StatusCheck(name='ALERT_TEST')
            check.save()
            StatusCheckResult.objects.create(
                status_check=check,
                time=timezone.now(),
                time_complete=timezone.now(),
                succeeded=new_status == Service.PASSING_STATUS)
            check.last_run = timezone.now()
            check.save()
            service.status_checks.add(check)
            service.users_to_notify.clear()
            service.users_to_notify.add(user)
            service.unexpired_acknowledgements().delete()
            Shift.objects.update(deleted=True)
            UserProfile.objects.update(fallback_alert_user=False)
            Shift(
                start=timezone.now() - timedelta(days=1),
                end=timezone.now() + timedelta(days=1),
                uid='test-shift',
                last_modified=timezone.now(),
                user=user
            ).save()
            service.alert()
            transaction.savepoint_rollback(sid)

    def post(self, request):
        form = AlertTestForm(request.POST)

        if form.is_valid():
            data = form.clean()
            service = data['service']
            self.trigger_alert_to_user(service, request.user, data['old_status'], data['new_status'])

            return JsonResponse({"result": "ok"})
        return JsonResponse({"result": "error"}, status=400)


class AlertTestPluginView(AlertTestView):
    def post(self, request):
        form = AlertTestPluginForm(request.POST)

        if form.is_valid():
            data = form.clean()

            with transaction.atomic():
                sid = transaction.savepoint()

                service = Service.objects.create(
                    name='test-alert-service'
                )
                service.alerts.add(data['alert_plugin'])
                self.trigger_alert_to_user(service, request.user, data['old_status'], data['new_status'])

                transaction.savepoint_rollback(sid)

            return JsonResponse({"result": "ok"})
        return JsonResponse({"result": "error"}, status=400)


class CoreSettingsForm(forms.Form):
    pass


class GeneralSettingsForm(forms.Form):
    first_name = forms.CharField(label='First name', max_length=30, required=False)
    last_name = forms.CharField(label='Last name', max_length=30, required=False)
    email_address = forms.CharField(label='Email Address', max_length=75,
                                    required=False)  # We use 75 and not the 254 because Django 1.6.8 only supports
    # 75. See commit message for details.
    enabled = forms.BooleanField(label='Enabled', required=False)


class InstanceListView(LoginRequiredMixin, CommonListView):
    model = Instance
    context_object_name = 'instances'

    def get_queryset(self):
        return Instance.objects.all().order_by('name').prefetch_related('status_checks')


class ServiceListView(LoginRequiredMixin, CommonListView):
    model = Service
    context_object_name = 'services'

    def get_queryset(self):
        return Service.objects.all().order_by('name').prefetch_related('status_checks')


class ServicePublicListView(TemplateView):
    model = Service
    context_object_name = 'services'
    template_name = "cabotapp/service_public_list.html"

    def get_context_data(self, **kwargs):
        context = super(ServicePublicListView, self).get_context_data(**kwargs)
        context[self.context_object_name] = Service.objects\
            .filter(is_public=True, alerts_enabled=True)\
            .order_by(Lower('name')).prefetch_related('status_checks')
        return context

class InstanceDetailView(LoginRequiredMixin, CommonDetailView):
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


class ServiceDetailView(LoginRequiredMixin, CommonDetailView):
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


class InstanceCreateView(LoginRequiredMixin, CommonCreateView):
    model = Instance
    form_class = InstanceForm

    def form_valid(self, form):
        ret = super(InstanceCreateView, self).form_valid(form)
        if self.object.status_checks.filter(polymorphic_ctype__model='icmpstatuscheck').count() == 0:
            self.generate_default_ping_check(self.object)
        return ret

    def generate_default_ping_check(self, obj):
        pc = ICMPStatusCheck(
            name="Default Ping Check for %s" % obj.name,
            frequency=5,
            importance=Service.ERROR_STATUS,
            debounce=0,
            created_by=None,
        )
        pc.save()
        obj.status_checks.add(pc)

    def get_success_url(self):
        return reverse('instance', kwargs={'pk': self.object.id})

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


class ServiceCreateView(LoginRequiredMixin, CommonCreateView):
    model = Service
    form_class = ServiceForm

    def __init__(self, *args, **kwargs):
        super(ServiceCreateView, self).__init__(*args, **kwargs)

    def get_success_url(self):
        return reverse('service', kwargs={'pk': self.object.id})


class InstanceUpdateView(LoginRequiredMixin, CommonUpdateView):
    model = Instance
    form_class = InstanceForm

    def get_success_url(self):
        return reverse('instance', kwargs={'pk': self.object.id})


class ServiceUpdateView(LoginRequiredMixin, CommonUpdateView):
    model = Service
    form_class = ServiceForm

    def get_success_url(self):
        return reverse('service', kwargs={'pk': self.object.id})


class ServiceDeleteView(LoginRequiredMixin, CommonDeleteView):
    model = Service
    success_url = reverse_lazy('services')
    context_object_name = 'service'
    template_name = 'cabotapp/service_confirm_delete.html'


class InstanceDeleteView(LoginRequiredMixin, CommonDeleteView):
    model = Instance
    success_url = reverse_lazy('instances')
    context_object_name = 'instance'
    template_name = 'cabotapp/instance_confirm_delete.html'


class ShiftListView(LoginRequiredMixin, CommonListView):
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


class SetupForm(forms.Form):
    username = forms.CharField(label='Username', max_length=100, required=True)
    email = forms.EmailField(label='Email', max_length=200, required=False)
    password = forms.CharField(label='Password', required=True, widget=forms.PasswordInput())


class SetupView(View):
    template = loader.get_template('cabotapp/setup.html')

    def get(self, request):
        if not cabot_needs_setup():
            return redirect('login')

        form = SetupForm(initial={
            'username': 'admin',
        })

        return HttpResponse(self.template.render({'form': form}, request))

    def post(self, request):
        if not cabot_needs_setup():
            return redirect('login')

        form = SetupForm(request.POST)
        if form.is_valid():
            get_user_model().objects.create_superuser(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
            return redirect('login')

        return HttpResponse(self.template.render({'form': form}, request), status=400)


class OnCallView(APIView):
    queryset = User.objects

    def get(self, request):
        users = get_duty_officers()

        users_json = []
        for user in users:
            plugin_data = {}
            for pluginuserdata in user.profile.alertpluginuserdata_set.all():
                plugin_data[pluginuserdata.title] = pluginuserdata.serialize()

            users_json.append({
                    "username": user.username,
                    "email": user.email,
                    "mobile_number": user.profile.mobile_number,
                    "plugin_data": plugin_data
                })

        return Response(users_json)


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


def about(request):
    """ Very simple about page """
    from cabot import version

    return render(request, 'cabotapp/about.html', {
        'cabot_version': version,
    })

def jsonify(d):
    return HttpResponse(json.dumps(d), content_type='application/json')


@login_required
def graphite_api_data(request):
    metric = request.GET.get('metric')
    if request.GET.get('frequency'):
        mins_to_check = int(request.GET.get('frequency'))
    else:
        mins_to_check = None
    data = None
    matching_metrics = None
    try:
        data = get_data(metric, mins_to_check)
    except requests.exceptions.RequestException, e:
        pass
    if not data:
        try:
            matching_metrics = get_matching_metrics(metric)
        except requests.exceptions.RequestException, e:
            return jsonify({'status': 'error', 'message': str(e)})
        matching_metrics = {'metrics': matching_metrics}
    return jsonify({'status': 'ok', 'data': data, 'matchingMetrics': matching_metrics})
