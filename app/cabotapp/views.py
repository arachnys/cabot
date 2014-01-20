from django.template import RequestContext, loader
from datetime import datetime, timedelta
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from models import (StatusCheck, GraphiteStatusCheck, JenkinsStatusCheck, HttpStatusCheck,
  StatusCheckResult, UserProfile, Service, Shift, get_duty_officers)
from tasks import run_status_check as _run_status_check
from tasks import update_service as _update_service
from tasks import run_all_checks as _run_all_checks
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, CreateView, UpdateView, ListView, DeleteView
from django import forms
from .graphite import get_data, get_matching_metrics
from .alert import telephone_alert_twiml_callback
from django.contrib.auth.models import User
from django.utils.timezone import utc
from django.core.urlresolvers import reverse

import requests
import json

class LoginRequiredMixin(object):
  @method_decorator(login_required)
  def dispatch(self, *args, **kwargs):
    return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)

@login_required
def subscriptions(request):
  """ Simple list of all checks """
  t = loader.get_template('cabotapp/subscriptions.html')
  services = Service.objects.all().order_by('alerts_enabled')
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


class StatusCheckResultDetailView(LoginRequiredMixin, DetailView):
  model = StatusCheckResult
  context_object_name = 'result'


class SymmetricalForm(forms.ModelForm):
  symmetrical_fields = () # Iterable of 2-tuples (field, model)

  def __init__(self, *args, **kwargs):
    super(SymmetricalForm, self).__init__(*args, **kwargs)

    if self.instance and self.instance.pk:
      for field in self.symmetrical_fields:
        self.fields[field].initial = getattr(self.instance, field).all()

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
      'frequency',
      'importance',
      'active',
      'debounce',
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
      'debounce',
      'max_queued_build_time',
    )
    widgets = dict(**base_widgets)

class UserProfileForm(forms.ModelForm):
  class Meta:
    model = UserProfile
    exclude = ('user',)


class ServiceForm(forms.ModelForm):
  class Meta:
    model = Service
    template_name = 'service_form.html'
    fields = (
      'name',
      'url',
      'users_to_notify',
      'status_checks',
      'email_alert',
      'hipchat_alert',
      'sms_alert',
      'telephone_alert',
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
      'users_to_notify': forms.CheckboxSelectMultiple(),
      'hackpad_id': forms.TextInput(attrs={'style': 'width:30%;'}),
    }

  def __init__(self, *args, **kwargs):
    ret = super(ServiceForm, self).__init__(*args, **kwargs)
    self.fields['users_to_notify'].queryset = User.objects.filter(is_active=True)
    return ret


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
    return reverse('check', kwargs={'pk': self.object.id})


class CheckUpdateView(LoginRequiredMixin, UpdateView):
  template_name = 'cabotapp/statuscheck_form.html'

  def get_success_url(self):
    return reverse('check', kwargs={'pk': self.object.id})


class GraphiteCheckCreateView(CheckCreateView):
  model = GraphiteStatusCheck
  form_class = GraphiteStatusCheckForm


class GraphiteCheckUpdateView(CheckUpdateView):
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


class JenkinsCheckUpdateView(CheckUpdateView):
  model = JenkinsStatusCheck
  form_class = JenkinsStatusCheckForm


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
    if context == None:
      context = {}
    context['checkresults'] = self.object.statuscheckresult_set.order_by('-time_complete')[:100]
    return super(StatusCheckDetailView, self).render_to_response(context, *args, **kwargs)


class UserProfileUpdateView(LoginRequiredMixin, UpdateView):
  model = UserProfile
  success_url = reverse_lazy('subscriptions')
  form_class = UserProfileForm

  def get_object(self, *args, **kwargs):
    try:
      return self.model.objects.get(user=self.kwargs['pk'])
    except self.model.DoesNotExist:
      user = User.objects.get(id=self.kwargs['pk'])
      profile = UserProfile(user=user)
      profile.save()
      return profile


class ServiceListView(LoginRequiredMixin, ListView):
  model = Service
  context_object_name = 'services'

  def get_queryset(self):
    return Service.objects.all().order_by('name').prefetch_related('status_checks')


class ServiceDetailView(LoginRequiredMixin, DetailView):
  model = Service
  context_object_name = 'service'


class ServiceCreateView(LoginRequiredMixin, CreateView):
  model = Service
  form_class = ServiceForm

  def get_success_url(self):
    return reverse('service', kwargs={'pk': self.object.id})


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


class ShiftListView(LoginRequiredMixin, ListView):
  model = Shift
  context_object_name = 'shifts'

  def get_queryset(self):
    return Shift.objects.filter(end__gt=datetime.utcnow().replace(tzinfo=utc),
      deleted=False).order_by('start')


### Misc JSON api and other stuff

def twiml_callback(request, service_id):
  service = Service.objects.get(id=service_id)
  twiml = telephone_alert_twiml_callback(service)
  return HttpResponse(twiml, content_type='application/xml')

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

@login_required
def graphite_api_data(request):
  metric = request.GET.get('metric')
  data = None
  matching_metrics = None
  try:
    data = get_data(metric)
  except requests.exceptions.RequestException, e:
    pass
  if not data:
    try:
      matching_metrics = get_matching_metrics(metric)
    except requests.exceptions.RequestException, e:
      return jsonify({'status': 'error', 'message': str(e)})
    matching_metrics = {'metrics': matching_metrics}
  return jsonify({'status': 'ok', 'data': data, 'matchingMetrics': matching_metrics})
