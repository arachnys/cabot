from django.contrib import admin
from cabot.cabotapp.modelcategories.user import UserProfile
from cabot.cabotapp.modelcategories.common import (Service, ServiceStatusSnapshot, Shift,
                                        StatusCheck, StatusCheckResult, Instance,
                                        AlertAcknowledgement)
from .alert import AlertPluginUserData, AlertPlugin

admin.site.register(UserProfile)
admin.site.register(Shift)
admin.site.register(Service)
admin.site.register(ServiceStatusSnapshot)
admin.site.register(StatusCheck)
admin.site.register(StatusCheckResult)
admin.site.register(Instance)
admin.site.register(AlertPlugin)
admin.site.register(AlertPluginUserData)
admin.site.register(AlertAcknowledgement)
