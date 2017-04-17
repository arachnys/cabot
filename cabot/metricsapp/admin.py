from django.contrib import admin
from cabot.metricsapp.models import ElasticsearchSource
from cabot.metricsapp.forms import ElasticsearchSourceForm


class ElasticsearchSourceAdmin(admin.ModelAdmin):
    form = ElasticsearchSourceForm


admin.site.register(ElasticsearchSource, ElasticsearchSourceAdmin)
