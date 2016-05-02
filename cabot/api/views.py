from django import forms
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from polymorphic.models import PolymorphicModel
from cabot.cabotapp import models, alert
from cabot.cabotapp.models import StatusCheck, Service
from cabot.cabotapp.views import StatusCheckViewMixin
from cabot.plugins.models import StatusCheckPluginModel
from rest_framework import routers, serializers, viewsets, mixins
from rest_framework.response import Response


from logging import getLogger
logger = getLogger(__name__)

def create_viewset(arg_model, arg_fields, arg_read_only_fields=(), no_create=False):

    arg_read_only_fields = ('id',) + arg_read_only_fields
    for field in arg_read_only_fields:
        if field not in arg_fields:
            arg_fields = arg_fields + (field,)

    class Serializer(serializers.ModelSerializer):
        class Meta:
            model = arg_model
            fields = arg_fields
            read_only_fields = arg_read_only_fields

    viewset_class = None
    if no_create:
        class NoCreateViewSet(mixins.RetrieveModelMixin,
                              mixins.UpdateModelMixin,
                              mixins.DestroyModelMixin,
                              mixins.ListModelMixin,
                              viewsets.GenericViewSet):
            pass
        viewset_class = NoCreateViewSet
    else:
        viewset_class = viewsets.ModelViewSet
    
    
    if issubclass(arg_model, PolymorphicModel):
        qs = arg_model.objects.instance_of(arg_model)
    else:
        qs = arg_model.objects.all()


    class ViewSet(viewset_class):
        queryset = qs
        serializer_class = Serializer
        ordering = ['id']
        filter_fields = arg_fields
    return ViewSet

check_group_mixin_fields = (
    'name',
    'users_to_notify',
    'alerts_enabled',
    'status_checks',
    'alerts',
    'hackpad_id',
)

ServiceViewSet =  create_viewset(
    arg_model=models.Service,
    arg_fields=check_group_mixin_fields + (
        'url',
        'instances',
        'overall_status',
    ),
)

InstanceViewSet =  create_viewset(
    arg_model=models.Instance,
    arg_fields=check_group_mixin_fields + (
        'address',
        'overall_status',
    ),
)


ShiftViewSet = create_viewset(
    arg_model=models.Shift,
    arg_fields=(
        'start',
        'end',
        'user',
        'uid',
        'deleted',
    )
)


class StatusCheckSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    check_plugin = serializers.CharField()
    name = serializers.CharField()
    active = serializers.BooleanField()
    importance = serializers.ChoiceField(
            choices = Service.IMPORTANCES)
    frequency = serializers.IntegerField()
    debounce = serializers.IntegerField()
    calculated_status = serializers.CharField()

class IStatusCheckSerializer(serializers.Serializer):

    # A mapping between form and serializers fields.
    serializer_field_mapping = {
	forms.BooleanField: serializers.BooleanField,
	forms.CharField: serializers.CharField,
	forms.DateField: serializers.DateField,
	forms.DateTimeField: serializers.DateTimeField,
	forms.DecimalField: serializers.DecimalField,
	forms.EmailField: serializers.EmailField,
	forms.Field: serializers.ModelField,
	forms.FileField: serializers.FileField,
	forms.FloatField: serializers.FloatField,
	forms.ImageField: serializers.ImageField,
	forms.IntegerField: serializers.IntegerField,
	forms.NullBooleanField: serializers.NullBooleanField,
	forms.SlugField: serializers.SlugField,
	forms.TimeField: serializers.TimeField,
	forms.URLField: serializers.URLField,
	forms.GenericIPAddressField: serializers.IPAddressField,
	forms.FilePathField: serializers.FilePathField,
        forms.ChoiceField: serializers.ChoiceField,
    }

    # This is a very simple function to get the default kwargs for a serializer
    # field. Validation is actually done by the form so there is no requirement
    # that this be perfect - just working.
    def get_field_kwargs(self, field_type, field):
        if field_type is forms.ChoiceField:
            return {'choices': ('x')}
        else:
            return {}

    
    def to_representation(self, instance):
        fields = {}

        config_form = instance.check_plugin.plugin_class.config_form
        for field in config_form().fields:

            f_field_type = config_form().fields[field].__class__
            field_type = self.serializer_field_mapping[f_field_type]
            field_kwargs = self.get_field_kwargs(f_field_type, field)

            fields[field] = field_type(**field_kwargs)

        S = type('SubClass',
                (StatusCheckSerializer, ),
                fields)

        return S(instance, context=self.context).to_representation(instance)
            

class StatusCheckViewSet(viewsets.ModelViewSet, StatusCheckViewMixin):

    queryset = StatusCheck.objects.all()
    ordering_fields = '__all__'
    filter_fields = '__all__'
    serializer_class = IStatusCheckSerializer
    filter_fields = ('name', 'check_plugin', 'active', 'importance',
            'frequency', 'debounce', 'calculated_status')

    def get_status_check_plugin(self):
        plugin_slug = self.request.data['check_plugin']
        plugin = StatusCheckPluginModel.objects.get(slug=plugin_slug)
        return plugin

    def update(self, request, pk):

        form = self.get_form_class()(request.data, instance=self.get_object())
        if form.is_valid():
            form.save()
            
            return Response(request.data, status=201)
        return Response(form.errors, status=400)

    def create(self, request):

        form = self.get_form_class()(request.data)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.check_plugin = self.get_status_check_plugin()
            instance.save()
            form.save_m2m()
            return HttpResponseRedirect(reverse('api:checks-detail', args=[instance.pk]))

        return Response(request.data, status=401)

