from django.contrib import admin
from .models import (
    UserProfile,
    Service,
    Shift,
    ServiceStatusSnapshot,
    StatusCheck,
    StatusCheckResult,
    Schedule,
    HipchatInstance,
    MatterMostInstance,
)
from .alert import AlertPluginUserData, AlertPlugin

admin.site.register(UserProfile)
admin.site.register(Shift)
admin.site.register(Service)
admin.site.register(ServiceStatusSnapshot)
admin.site.register(StatusCheck)
admin.site.register(StatusCheckResult)
admin.site.register(AlertPlugin)
admin.site.register(AlertPluginUserData)
admin.site.register(Schedule)
admin.site.register(HipchatInstance)
admin.site.register(MatterMostInstance)
