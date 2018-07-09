from polymorphic import PolymorphicModel
from cabot.cabotapp import models, alert
from rest_framework import routers, serializers, viewsets, mixins
import logging

logger = logging.getLogger(__name__)

router = routers.DefaultRouter()


def create_viewset(arg_model,
                   arg_fields,
                   arg_read_only_fields=(),
                   no_create=False):
    '''
    Construct and return a ViewSet object:
    - http://www.django-rest-framework.org/api-guide/viewsets/
    '''

    # Construct the list of model fields using (id, fields, read-only fields)
    arg_read_only_fields = ('id',) + arg_read_only_fields
    for field in arg_read_only_fields:
        if field not in arg_fields:
            arg_fields = arg_fields + (field,)

    # Create a ModelSerializer class using the given model and fields.
    # http://www.django-rest-framework.org/api-guide/serializers/#modelserializer
    class Serializer(serializers.ModelSerializer):
        class Meta:
            model = arg_model
            fields = arg_fields
            read_only_fields = arg_read_only_fields

    # Create a ViewSet class that either does or does not allow for creation
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

    # Construct the queryset (ie. the list of model objects)
    arg_queryset = None
    if issubclass(arg_model, PolymorphicModel):
        arg_queryset = arg_model.objects.instance_of(arg_model)
    else:
        arg_queryset = arg_model.objects.all()

    # Construct and return the ViewSet class
    class ViewSet(viewset_class):
        queryset = arg_queryset
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

router.register(r'services', create_viewset(
    arg_model=models.Service,
    arg_fields=check_group_mixin_fields + (
        'url',
    ),
))

status_check_fields = (
    'name',
    'active',
    'importance',
    'frequency',
    'retries',
)

router.register(r'status-checks', create_viewset(
    arg_model=models.StatusCheck,
    arg_fields=status_check_fields,
    no_create=True,
))

router.register(r'http-checks', create_viewset(
    arg_model=models.HttpStatusCheck,
    arg_fields=status_check_fields + (
        'endpoint',
        'username',
        'password',
        'text_match',
        'status_code',
        'timeout',
        'verify_ssl_certificate',
    ),
))

router.register(r'jenkins-checks', create_viewset(
    arg_model=models.JenkinsStatusCheck,
    arg_fields=status_check_fields + (
        'max_queued_build_time',
    ),
))

router.register(r'tcp-checks', create_viewset(
    arg_model=models.TCPStatusCheck,
    arg_fields=status_check_fields + (
        'address',
        'port',
        'timeout',
    ),
))

'''
Omitting user API, could expose/allow modifying dangerous fields.

router.register(r'users', create_viewset(
    arg_model=django_models.User,
    arg_fields=(
        'password',
        'is_active',
        'groups',
        #'user_permissions', # Doesn't work, removing for now
        'username',
        'first_name',
        'last_name',
        'email',
    ),
))

router.register(r'user-profiles', create_viewset(
    arg_model=models.UserProfile,
    arg_fields=(
        'user',
        'mobile_number',
        'hipchat_alias',
    ),
))
'''

router.register(r'shifts', create_viewset(
    arg_model=models.Shift,
    arg_fields=(
        'start',
        'end',
        'user',
        'uid',
        'deleted',
    )
))

router.register(r'alert-plugins', create_viewset(
    arg_model=alert.AlertPlugin,
    arg_fields=(
            'title',
        )
    ))
