from django.contrib import admin
from .models import UserProfile, Service, Shift, ServiceStatusSnapshot, StatusCheck, StatusCheckResult

admin.site.register(UserProfile)
admin.site.register(Shift)
admin.site.register(Service)
admin.site.register(ServiceStatusSnapshot)
admin.site.register(StatusCheck)
admin.site.register(StatusCheckResult)
