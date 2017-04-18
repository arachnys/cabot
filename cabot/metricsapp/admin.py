from django.contrib import admin
from cabot.metricsapp.models import ElasticsearchSource, ElasticsearchStatusCheck
from cabot.metricsapp.forms import ElasticsearchSourceForm, ElasticsearchStatusCheckForm


class ElasticsearchSourceAdmin(admin.ModelAdmin):
    form = ElasticsearchSourceForm


class ElasticsearchStatusCheckAdmin(admin.ModelAdmin):
    form = ElasticsearchStatusCheckForm


admin.site.register(ElasticsearchSource, ElasticsearchSourceAdmin)
admin.site.register(ElasticsearchStatusCheck, ElasticsearchStatusCheckAdmin)
