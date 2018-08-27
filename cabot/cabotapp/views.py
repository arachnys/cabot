from django.template import RequestContext, loader
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from django.conf import settings
from models import (StatusCheck,
                    JenkinsStatusCheck,
                    HttpStatusCheck,
                    TCPStatusCheck,
                    StatusCheckResult,
                    ActivityCounter,
                    UserProfile,
                    Service,
                    Shift,
                    Schedule,
                    get_all_duty_officers,
                    get_single_duty_officer,
                    get_all_fallback_officers,
                    update_shifts)

from tasks import run_status_check as _run_status_check
from .decorators import cabot_login_required
from django.utils.decorators import method_decorator
from django.views.generic import (DetailView,
                                  CreateView,
                                  UpdateView,
                                  ListView,
                                  DeleteView,
                                  TemplateView,
                                  View)
from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.timezone import utc
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.db import transaction

from cabot.cabotapp import alert
from models import AlertPluginUserData
from django.contrib import messages
from social.exceptions import AuthFailed
from social.apps.django_app.views import complete

from itertools import groupby, dropwhile, izip_longest
import requests
import json
import re
from icalendar import Calendar
from django.template.defaulttags import register

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


class LoginRequiredMixin(object):

    @method_decorator(cabot_login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


@cabot_login_required
def subscriptions(request):
    """ Simple list of all checks """
    t = loader.get_template('cabotapp/subscriptions.html')
    services = Service.objects.all()
    users = User.objects.filter(is_active=True)
    c = RequestContext(request, {
        'services': services,
        'users': users,
        'duty_officers': get_all_duty_officers(),
        'fallback_officers': get_all_fallback_officers(),
    })
    return HttpResponse(t.render(c))


@cabot_login_required
def run_status_check(request, pk):
    """Runs a specific check"""
    _run_status_check(pk=pk)
    return HttpResponseRedirect(reverse('check', kwargs={'pk': pk}))


def duplicate_check(request, pk):
    check = StatusCheck.objects.get(pk=pk)
    new_pk = check.duplicate()
    return HttpResponseRedirect(reverse('check', kwargs={'pk': new_pk}))


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


class StatusCheckForm(SymmetricalForm):
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


class HttpStatusCheckForm(StatusCheckForm):
    class Meta:
        model = HttpStatusCheck
        fields = (
            'name',
            'endpoint',
            'http_method',
            'username',
            'password',
            'http_params',
            'http_body',
            'text_match',
            'header_match',
            'allow_http_redirects',
            'status_code',
            'timeout',
            'verify_ssl_certificate',
            'frequency',
            'importance',
            'active',
            'retries',
            'use_activity_counter',
            'runbook',
        )
        widgets = dict(**base_widgets)
        widgets.update({
            'endpoint': forms.TextInput(attrs={
                'style': 'width: 100%',
                'placeholder': 'https://www.arachnys.com',
            }),
            'username': forms.TextInput(attrs={
                'style': 'width: 30%',
            }),
            'password': forms.TextInput(attrs={
                'style': 'width: 30%',
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


class JenkinsStatusCheckForm(StatusCheckForm):
    class Meta:
        model = JenkinsStatusCheck
        fields = (
            'name',
            'importance',
            'retries',
            'max_queued_build_time',
            'max_build_failures',
            'use_activity_counter',
            'runbook',
        )
        widgets = dict(**base_widgets)


class TCPStatusCheckForm(StatusCheckForm):
    class Meta:
        model = TCPStatusCheck
        fields = (
            'name',
            'address',
            'port',
            'timeout',
            'frequency',
            'importance',
            'active',
            'retries',
            'use_activity_counter',
            'runbook',
        )
        widgets = dict(**base_widgets)
        widgets.update({
            'address': forms.TextInput(attrs={
                'style': 'width:50%',
            })
        })


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        template_name = 'service_form.html'
        fields = (
            'name',
            'url',
            'users_to_notify',
            'schedules',
            'status_checks',
            'alerts',
            'alerts_enabled',
            'hipchat_instance',
            'hipchat_room_id',
            'hackpad_id',
        )
        widgets = {
            'name': forms.TextInput(attrs={'style': 'width: 30%;'}),
            'url': forms.TextInput(attrs={'style': 'width: 70%;'}),
            'status_checks': forms.SelectMultiple(attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            }),
            'alerts': forms.SelectMultiple(attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            }),
            'users_to_notify': forms.CheckboxSelectMultiple(),
            'schedules': forms.CheckboxSelectMultiple(),
            'hipchat_instances': forms.SelectMultiple(attrs={
                'data-rel': 'chosen',
                'style': 'width: 70%',
            }),
            'hackpad_id': forms.TextInput(attrs={'style': 'width:30%;'}),
        }

    def __init__(self, *args, **kwargs):
        ret = super(ServiceForm, self).__init__(*args, **kwargs)
        self.fields['users_to_notify'].queryset = User.objects.filter(
            is_active=True)
        self.fields['schedules'].queryset = Schedule.objects.all()
        return ret

    def clean_hackpad_id(self):
        value = self.cleaned_data['hackpad_id']
        if not value:
            return ''
        for pattern in settings.RECOVERY_SNIPPETS_WHITELIST:
            if re.match(pattern, value):
                return value
        raise ValidationError('Please specify a valid JS snippet link')


class ScheduleForm(SymmetricalForm):
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
        model = Schedule
        template_name = 'schedule_form.html'
        fields = (
            'name',
            'ical_url',
            'fallback_officer',
        )
        widgets = {
            'name': forms.TextInput(attrs={'style': 'width: 80%;'}),
            'ical_url': forms.TextInput(attrs={'style': 'width: 80%;'}),
            'fallback_officer': forms.Select()
        }

    def clean_ical_url(self):
        """
        Make sure the input ical url data can be parsed.
        :return: the ical url if valid, otherwise raise an exception
        """
        try:
            ical_url = self.cleaned_data['ical_url']
            resp = requests.get(ical_url)
            Calendar.from_ical(resp.content)
            return ical_url
        except Exception:
            raise ValidationError('Invalid ical url {}'.format(self.cleaned_data['ical_url']))

    def __init__(self, *args, **kwargs):
        return super(ScheduleForm, self).__init__(*args, **kwargs)
        self.fields['fallback_officer'].queryset = User.objects.filter(is_active=True) \
            .order_by('username')


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


class CheckCreateView(LoginRequiredMixin, CreateView):
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

        if service_id:
            try:
                service = Service.objects.get(id=service_id)
                initial['service_set'] = [service]
            except Service.DoesNotExist:
                pass

        return initial

    def get_success_url(self):
        if self.request.GET.get('service'):
            return reverse('service', kwargs={'pk': self.request.GET.get('service')})
        return reverse('check', kwargs={'pk': self.object.id})


class CheckUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'cabotapp/statuscheck_form.html'

    def get_success_url(self):
        return reverse('check', kwargs={'pk': self.object.id})


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


class TCPCheckCreateView(CheckCreateView):
    model = TCPStatusCheck
    form_class = TCPStatusCheckForm


class TCPCheckUpdateView(CheckUpdateView):
    model = TCPStatusCheck
    form_class = TCPStatusCheckForm


class StatusCheckListView(LoginRequiredMixin, ListView):
    model = StatusCheck
    context_object_name = 'checks'

    def get_queryset(self):
        return StatusCheck.objects.all().order_by('name').prefetch_related('service_set')


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


class UserProfileUpdateView(LoginRequiredMixin, View):
    model = AlertPluginUserData

    def get(self, *args, **kwargs):
        return HttpResponseRedirect(reverse('update-alert-user-data', args=(self.kwargs['pk'], u'General')))


class UserProfileUpdateAlert(LoginRequiredMixin, View):
    template = loader.get_template('cabotapp/alertpluginuserdata_form.html')
    model = AlertPluginUserData

    def get(self, request, pk, alerttype):
        if request.user.id != int(pk) and not request.user.is_superuser:
            return HttpResponse(status=403)

        try:
            profile = UserProfile.objects.get(user=pk)
        except UserProfile.DoesNotExist:
            user = User.objects.get(id=pk)
            profile = UserProfile(user=user)
            profile.save()

        profile.user_data()

        if (alerttype == u'General'):
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

        c = RequestContext(request, {
            'form': form,
            'alert_preferences': profile.user_data(),
            })
        return HttpResponse(self.template.render(c))

    def post(self, request, pk, alerttype):
        if request.user.id != int(pk) and not request.user.is_superuser:
            return HttpResponse(status=403)

        profile = UserProfile.objects.get(user=pk)
        if (alerttype == u'General'):
            form = GeneralSettingsForm(request.POST)
            if form.is_valid():
                profile.user.first_name = form.cleaned_data['first_name']
                profile.user.last_name = form.cleaned_data['last_name']
                profile.user.is_active = form.cleaned_data['enabled']
                profile.user.email = form.cleaned_data['email_address']
                profile.user.save()
                profile.save()
                return HttpResponseRedirect(reverse('update-alert-user-data', args=(self.kwargs['pk'], alerttype)))

        else:
            plugin_userdata = self.model.objects.get(title=alerttype, user=profile)
            form_model = get_object_form(type(plugin_userdata))
            form = form_model(request.POST, instance=plugin_userdata)
            if form.is_valid() and not form.errors:
                form.save()
                return HttpResponseRedirect(reverse('update-alert-user-data', args=(self.kwargs['pk'], alerttype)))
            else:
                c = RequestContext(request, {
                    'form': form,
                    'alert_preferences': profile.user_data,
                })
                return HttpResponse(self.template.render(c))


def get_object_form(model_type):
    class AlertPreferencesForm(forms.ModelForm):
        class Meta:
            model = model_type

        def is_valid(self):
            return True

        def clean_phone_number(self):
            phone_number = self.cleaned_data['phone_number']
            if any(not n.isdigit() for n in phone_number):
                raise ValidationError('Phone number should only contain numbers. '
                                      'Format: CNNNNNNNNNN, where C is the country code (1 for USA)')

            # 10 digit phone number + 1+ digit country code
            if len(phone_number) < 11:
                raise ValidationError('Phone number should include a country code. '
                                      'Format: CNNNNNNNNNN, where C is the country code (1 for USA)')

            return phone_number

        def clean_hipchat_alias(self):
            hipchat_alias = self.cleaned_data['hipchat_alias']
            if hipchat_alias.startswith('@'):
                raise ValidationError('Do not include leading @ in Hipchat alias')
            return hipchat_alias

    return AlertPreferencesForm


class GeneralSettingsForm(forms.Form):
    first_name = forms.CharField(label='First name', max_length=30, required=False)
    last_name = forms.CharField(label='Last name', max_length=30, required=False)
    email_address = forms.CharField(label='Email Address', max_length=30, required=False)
    enabled = forms.BooleanField(label='Enabled', required=False)


class ServiceListView(LoginRequiredMixin, ListView):
    model = Service
    context_object_name = 'services'

    def get_queryset(self):
        return Service.objects.all().order_by('name').prefetch_related('status_checks')

    def get_context_data(self, **kwargs):
        context = super(ServiceListView, self).get_context_data(**kwargs)
        context['service_image'] = settings.SERVICE_IMAGE
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


class ServiceCreateView(LoginRequiredMixin, CreateView):
    model = Service
    form_class = ServiceForm

    alert.update_alert_plugins()

    def get_success_url(self):
        return reverse('service', kwargs={'pk': self.object.id})


class ScheduleCreateView(LoginRequiredMixin, CreateView):
    model = Schedule
    form_class = ScheduleForm
    success_url = reverse_lazy('shifts')


class ServiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Service
    form_class = ServiceForm

    def get_success_url(self):
        return reverse('service', kwargs={'pk': self.object.id})


class ScheduleUpdateView(LoginRequiredMixin, UpdateView):
    model = Schedule
    form_class = ScheduleForm
    context_object_name = 'schedules'
    success_url = reverse_lazy('shifts')


class ServiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Service
    success_url = reverse_lazy('services')
    context_object_name = 'service'
    template_name = 'cabotapp/service_confirm_delete.html'


class ScheduleDeleteView(LoginRequiredMixin, DeleteView):
    model = Schedule
    form_class = ScheduleForm

    success_url = reverse_lazy('shifts')
    context_object_name = 'schedule'
    template_name = 'cabotapp/schedule_confirm_delete.html'


class ScheduleListView(LoginRequiredMixin, ListView):
    model = Schedule
    context_object_name = 'schedules'

    def get_queryset(self):
        return Schedule.objects.all().order_by('id')

    def get_context_data(self, **kwargs):
        """Add current duty officer to list page"""
        context = super(ScheduleListView, self).get_context_data(**kwargs)
        duty_officers = {schedule: get_single_duty_officer(schedule) for schedule in Schedule.objects.all()}
        context['duty_officers'] = {
            'officers': duty_officers,
        }
        return context


class ShiftListView(LoginRequiredMixin, ListView):
    model = Shift
    context_object_name = 'shifts'

    def get_queryset(self):
        schedule = Schedule.objects.get(id=self.kwargs['pk'])
        update_shifts(schedule)
        return Shift.objects.filter(
            end__gt=datetime.utcnow().replace(tzinfo=utc),
            deleted=False,
            schedule=schedule).order_by('start')

    def get_context_data(self, **kwargs):
        context = super(ShiftListView, self).get_context_data(**kwargs)

        context['schedule'] = Schedule.objects.get(id=self.kwargs['pk'])
        context['schedule_id'] = self.kwargs['pk']
        return context


class StatusCheckReportView(LoginRequiredMixin, TemplateView):
    template_name = 'cabotapp/statuscheck_report.html'

    def get_context_data(self, **kwargs):
        form = StatusCheckReportForm(self.request.GET)
        if form.is_valid():
            return {'checks': form.get_report(), 'service': form.cleaned_data['service']}


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


def json_response(data, code, pretty=False):
    '''
    Return a JSON response containing some data. Supports pretty-printing.
    '''
    dump_opts = {}
    if pretty:
        dump_opts = {'sort_keys': True, 'indent': 4, 'separators': (',', ': ')}
    content = json.dumps(data, **dump_opts) + "\n"
    return HttpResponse(content, status=code, content_type="application/json")


def json_error_response(message, code):
    '''Return a JSON response with an error message'''
    return json_response({'detail': message}, code)


class AuthComplete(View):
    def get(self, request, *args, **kwargs):
        backend = kwargs.pop('backend')
        try:
            return complete(request, backend, *args, **kwargs)
        except AuthFailed:
            messages.error(request, "Your domain isn't authorized")
            return HttpResponseRedirect(reverse('login'))


class LoginError(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse(status=401)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


class ViewError(Exception):
    '''
    A general-purpose HTTP request-processing exception that carries both an
    error message and HTTP status code to be returned to the client.
    '''
    def __init__(self, message, code):
        super(ViewError, self).__init__(message)
        self.code = code


class ActivityCounterView(View):

    # Enable transactions to prevent race conditions when multiple requests are
    # reading and updating a counter.
    @transaction.atomic
    def get(self, request, pk):
        '''Handle an HTTP GET request'''
        id = request.GET.get('id', None)
        name = request.GET.get('name', None)

        # We require the name or id of a check
        if not (id or name):
            return json_error_response('Please provide a name or id', 400)

        try:
            # Lookup the check and make sure it has a related ActivityCounter
            check = self._lookup_check(id, name)
            ActivityCounter.objects.get_or_create(status_check=check)

            # Perform the action and return the result
            action = request.GET.get('action', 'read')
            pretty = request.GET.get('pretty') == 'true'
            message = self._handle_action(check, action)

        except ViewError as e:
            return json_error_response(e.message, e.code)

        data = {
            'check.id': check.id,
            'check.name': check.name,
            'counter.count': check.activity_counter.count,
            'counter.enabled': check.use_activity_counter,
        }
        if message:
            data['detail'] = message
        return json_response(data, 200, pretty=pretty)

    def _lookup_check(self, id, name):
        '''
        Lookup the check by id or name. Id is preferred.
        - Returns a StatusCheck object.
        - Will raise a ViewError if no check is found.
        '''
        checks = None
        if id:
            checks = StatusCheck.objects.filter(id=id)
        if name and not checks:
            checks = StatusCheck.objects.filter(name=name)
            if checks and len(checks) > 1:
                raise ViewError("Multiple checks found with name '{}'".format(name), 500)
        if not checks:
            raise ViewError('Check not found', 404)
        return checks.first()

    def _handle_action(self, check, action):
        '''
        Perform the given action on the check.
        - Return a message to be sent back in the response, or None.
        - Raises a ViewError if given an invalid action.
        '''
        if action == 'read':
            return None

        if action == 'incr':
            check.activity_counter.count += 1
            check.activity_counter.save()
            return 'counter incremented to {}'.format(check.activity_counter.count)

        if action == 'decr':
            if check.activity_counter.count > 0:
                check.activity_counter.count -= 1
                check.activity_counter.save()
            return 'counter decremented to {}'.format(check.activity_counter.count)

        if action == 'reset':
            if check.activity_counter.count > 0:
                check.activity_counter.count = 0
                check.activity_counter.save()
            return 'counter reset to 0'

        raise ViewError("invalid action '{}'".format(action), 400)
