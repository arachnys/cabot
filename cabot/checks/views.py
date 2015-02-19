from django.shortcuts import render
from django.views.generic import CreateView
from cabot.cabotapp.views import LoginRequiredMixin
from .models import CheckPlugin

class CheckCreateView(LoginRequiredMixin, CreateView):
    template_name = 'cabotapp/statuscheck_form.html'

    def get(self, request, plugin_name):

        for plugin in CheckPlugin.__subclasses__():
            logger.error(plugin.plugin_name)
            if urllib.unquote_plus(plugin_name) == plugin.plugin_name:
                self.model = plugin
                self.form_class = ICMPStatusCheckForm

        return super(CreateView, self).get(request, plugin_name)

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
