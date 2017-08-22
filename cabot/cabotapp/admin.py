from django.contrib import admin
from polymorphic.admin import (PolymorphicChildModelAdmin,
                               PolymorphicParentModelAdmin)

from .alert import AlertPlugin, AlertPluginUserData
from .models import (AlertAcknowledgement, Instance, JenkinsConfig, Service,
                     ServiceStatusSnapshot, Shift, StatusCheck,
                     StatusCheckResult, UserProfile)


class StatusCheckAdmin(PolymorphicParentModelAdmin):
    base_model = StatusCheck
    child_models = StatusCheck.__subclasses__()


class ChildStatusCheckAdmin(PolymorphicChildModelAdmin):
    base_model = StatusCheck


for child_status_check in StatusCheck.__subclasses__():
    admin.site.register(child_status_check, ChildStatusCheckAdmin)

admin.site.register(UserProfile)
admin.site.register(Shift)
admin.site.register(Service)
admin.site.register(ServiceStatusSnapshot)
admin.site.register(StatusCheck, StatusCheckAdmin)
admin.site.register(StatusCheckResult)
admin.site.register(Instance)
admin.site.register(AlertPlugin)
admin.site.register(AlertPluginUserData)
admin.site.register(AlertAcknowledgement)
admin.site.register(JenkinsConfig)
