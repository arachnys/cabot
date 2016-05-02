from django.contrib import admin
from .models import PluginModel, AlertPluginUserData

admin.site.register(PluginModel)
admin.site.register(AlertPluginUserData)

