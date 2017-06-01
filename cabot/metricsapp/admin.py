from django.contrib import admin
from cabot.metricsapp.models import ElasticsearchSource, ElasticsearchStatusCheck, \
    GrafanaDataSource, GrafanaInstance
from cabot.metricsapp.forms import ElasticsearchSourceForm, ElasticsearchStatusCheckForm, \
    GrafanaDataSourceAdminForm, GrafanaInstanceAdminForm


class ElasticsearchSourceAdmin(admin.ModelAdmin):
    form = ElasticsearchSourceForm


class ElasticsearchStatusCheckAdmin(admin.ModelAdmin):
    form = ElasticsearchStatusCheckForm


class GrafanaInstanceAdmin(admin.ModelAdmin):
    form = GrafanaInstanceAdminForm


class GrafanaDataSourceAdmin(admin.ModelAdmin):
    form = GrafanaDataSourceAdminForm


admin.site.register(ElasticsearchSource, ElasticsearchSourceAdmin)
admin.site.register(ElasticsearchStatusCheck, ElasticsearchStatusCheckAdmin)
admin.site.register(GrafanaDataSource, GrafanaDataSourceAdmin)
admin.site.register(GrafanaInstance, GrafanaInstanceAdmin)
