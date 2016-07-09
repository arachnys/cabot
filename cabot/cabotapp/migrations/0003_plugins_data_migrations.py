# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-07-09 13:20
from __future__ import unicode_literals

from django.db import migrations
from django.contrib.contenttypes.management import update_contenttypes
from django.contrib.contenttypes.models import ContentType

import logging
logger = logging.getLogger(__name__)

def migrate_user_data(apps, schema_editor):
    OldAlertPluginUserData = apps.get_model('cabotapp', 'AlertPluginUserData')
    UserProfile = apps.get_model('cabotapp', 'UserProfile')
    AlertPluginUserData = apps.get_model('plugins', 'AlertPluginUserData')
    AlertPluginModel = apps.get_model('plugins', 'AlertPluginModel')

    # Update ContentTypes to include new plugin tables
    update_contenttypes(apps.get_app_config('plugins'))

    unique_alert_plugin_ctype_ids = OldAlertPluginUserData.objects.values_list(
                                'polymorphic_ctype_id', flat=True).distinct()

    for ud_type_id in unique_alert_plugin_ctype_ids:
        ud_type = ContentType.objects.get_for_id(ud_type_id)
        
        # Manually move alert plugin data. The plugins have changed and there
        # is no guarantee that the models are available/updated.
        cursor = schema_editor.connection.cursor()
        table_name = '{}_{}'.format(ud_type.app_label, ud_type.model)

        cursor.execute('SELECT * FROM {}'.format(table_name))

        for row in cursor.fetchall():
            field_names = [f[0] for f in cursor.description]
            vals = dict(zip(field_names, row))

            old_ud = OldAlertPluginUserData.objects.get(
                pk = vals.pop('alertpluginuserdata_ptr_id'),
            )

            user = old_ud.user.user

            # We guess this. It will work 90% of the time. The rest of the time
            # is the responsibility of the plugin author to sort out :P
            plugin_slug = ud_type.app_label
            plugin, created = AlertPluginModel.objects.get_or_create(
                slug = plugin_slug,
                polymorphic_ctype_id = ContentType.objects.get_for_model(
                                                AlertPluginModel).id
            )

            for key, value in vals.iteritems():
                AlertPluginUserData.objects.create(
                    user = user,
                    plugin = plugin,
                    key = key,
                    value = value,
                )


def migrate_service_alerts(apps, schema_editor):
    AlertPluginModel = apps.get_model('plugins', 'AlertPluginModel')
    Service = apps.get_model('cabotapp', 'Service')

    # Update ContentTypes to include new plugin tables
    update_contenttypes(apps.get_app_config('plugins'))

    for service in Service.objects.all():
        for alert in service.alerts.all():
            alert_ct = ContentType.objects.get_for_id(alert.polymorphic_ctype_id)
            plugin_slug = alert_ct.app_label

            plugin, created = AlertPluginModel.objects.get_or_create(
                slug = plugin_slug,
                polymorphic_ctype_id = ContentType.objects.get_for_model(AlertPluginModel).id,
            )

            service.alert_plugin_models.add(plugin)
            service.save()

    return

def migrate_old_status_checks(apps, schema_editor):
    
    # Mapping between old model names and new plugin names.
    status_check_models = {
        'icmpstatuscheck': 'cabot_check_icmp',
        'httpstatuscheck': 'cabot_check_http',
        'jenkinsstatuscheck': 'cabot_check_jenkins',
        'graphitestatuscheck': 'cabot_check_graphite',
    }

    StatusCheck = apps.get_model('cabotapp', 'StatusCheck')
    StatusCheckPluginModel = apps.get_model('plugins', 'StatusCheckPluginModel')
    StatusCheckVariable = apps.get_model('cabotapp', 'StatusCheckVariable')
    PluginModel = apps.get_model('plugins', 'PluginModel')

    # Update ContentTypes to include new plugin tables
    update_contenttypes(apps.get_app_config('plugins'))

    for sc in StatusCheck.objects.all():

        # Get or create status check plugins and link to status checks
        # appropriately.
        sc_type_id = sc.polymorphic_ctype_id
        sc_type = ContentType.objects.get_for_id(sc_type_id)

        sc_check_type = status_check_models[sc_type.model]
        sc_plugin, created = StatusCheckPluginModel.objects.get_or_create(
                slug = sc_check_type,
                polymorphic_ctype_id = ContentType.objects.get_for_model(
                                                StatusCheckPluginModel).id
                )

        sc.check_plugin_id = sc_plugin.id
        sc.save()

        # Migrate plugin specific variables to StatusCheckVariable objects

        def sc_set_variable(key, value):
            StatusCheckVariable.objects.create(
                status_check=sc,
                key=key,
                value=value
            )

        if sc_check_type == 'cabot_check_http':
            sc_set_variable('endpoint', sc.endpoint)
            sc_set_variable('username', sc.username)
            sc_set_variable('password', sc.password)
            sc_set_variable('text_match', sc.text_match)
            sc_set_variable('status_code', sc.status_code)
            sc_set_variable('timeout', sc.timeout)
            sc_set_variable('verify_ssl_certificate', sc.verify_ssl_certificate)

        elif sc_check_type == 'cabot_check_graphite':
            sc_set_variable('metric', sc.metric)
            sc_set_variable('check_type', sc.check_type)
            sc_set_variable('value', sc.value)
            sc_set_variable('expected_num_hosts', sc.expected_num_hosts)
            sc_set_variable('allowed_num_failures', sc.allowed_num_failures)

        elif sc_check_type == 'cabot_check_jenkins':
            sc_set_variable('max_queued_build_time', sc.max_queued_build_time)


    return


class Migration(migrations.Migration):

    dependencies = [
        ('cabotapp', '0002_create_plugin_models'),
        ('plugins', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_old_status_checks),
        migrations.RunPython(migrate_service_alerts),
        migrations.RunPython(migrate_user_data),
    ]
