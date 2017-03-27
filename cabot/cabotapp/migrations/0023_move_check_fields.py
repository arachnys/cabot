# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        """
        Add data to tables for subclasses.
        """
        # influx checks are subsets of graphite checks, so we can do both at once
        graphite_status_checks = orm.StatusCheck.objects.filter(polymorphic_ctype__model='graphitestatuscheck')
        for sc in graphite_status_checks:
            orm.GraphiteStatusCheck.objects.create(id=sc.id,
                                                   polymorphic_ctype_id=sc.polymorphic_ctype_id,
                                                   name=sc.name,
                                                   active=sc.active,
                                                   importance=sc.importance,
                                                   frequency=sc.frequency,
                                                   debounce=sc.debounce,
                                                   created_by_id=sc.created_by_id,
                                                   calculated_status=sc.calculated_status,
                                                   last_run=sc.last_run,
                                                   cached_health=sc.cached_health,
                                                   check_type=sc.rcheck_type,
                                                   value=sc.rvalue,
                                                   metric=sc.rmetric,
                                                   metric_selector=sc.rmetric_selector,
                                                   group_by=sc.rgroup_by,
                                                   fill_empty=sc.rfill_empty,
                                                   where_clause=sc.rwhere_clause,
                                                   expected_num_hosts=sc.rexpected_num_hosts,
                                                   expected_num_metrics=sc.rexpected_num_metrics,
                                                   interval=sc.rinterval)

        http_status_checks = orm.StatusCheck.objects.filter(polymorphic_ctype__model='httpstatuscheck')
        for sc in http_status_checks:
            orm.HttpStatusCheck.objects.create(id=sc.id,
                                               polymorphic_ctype_id=sc.polymorphic_ctype_id,
                                               name=sc.name,
                                               active=sc.active,
                                               importance=sc.importance,
                                               frequency=sc.frequency,
                                               debounce=sc.debounce,
                                               created_by_id=sc.created_by_id,
                                               calculated_status=sc.calculated_status,
                                               last_run=sc.last_run,
                                               cached_health=sc.cached_health,
                                               status_code=sc.rstatus_code,
                                               endpoint=sc.rendpoint,
                                               username=sc.rusername,
                                               password=sc.rpassword,
                                               http_method=sc.rhttp_method,
                                               http_params=sc.rhttp_params,
                                               http_body=sc.rhttp_body,
                                               allow_http_redirects=sc.rallow_http_redirects,
                                               text_match=sc.rtext_match,
                                               header_match=sc.rheader_match,
                                               timeout=sc.rtimeout,
                                               verify_ssl_certificate=sc.rverify_ssl_certificate)

        jenkins_status_checks = orm.StatusCheck.objects.filter(polymorphic_ctype__model='jenkinsstatuscheck')
        for sc in jenkins_status_checks:
            orm.JenkinsStatusCheck.objects.create(id=sc.id,
                                                  polymorphic_ctype_id=sc.polymorphic_ctype_id,
                                                  name=sc.name,
                                                  active=sc.active,
                                                  importance=sc.importance,
                                                  frequency=sc.frequency,
                                                  debounce=sc.debounce,
                                                  created_by_id=sc.created_by_id,
                                                  calculated_status=sc.calculated_status,
                                                  last_run=sc.last_run,
                                                  cached_health=sc.cached_health,
                                                  max_queued_build_time=sc.rmax_queued_build_time)

        icmp_status_checks = orm.StatusCheck.objects.filter(polymorphic_ctype__model='icmpstatuscheck')
        for sc in icmp_status_checks:
            orm.ICMPStatusCheck.objects.create(id=sc.id,
                                               polymorphic_ctype_id=sc.polymorphic_ctype_id,
                                               name=sc.name,
                                               active=sc.active,
                                               importance=sc.importance,
                                               frequency=sc.frequency,
                                               debounce=sc.debounce,
                                               created_by_id=sc.created_by_id,
                                               calculated_status=sc.calculated_status,
                                               last_run=sc.last_run,
                                               cached_health=sc.cached_health)

    def backwards(self, orm):
        pass

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'cabotapp.alertplugin': {
            'Meta': {'object_name': 'AlertPlugin'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'polymorphic_cabotapp.alertplugin_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'cabotapp.alertpluginuserdata': {
            'Meta': {'unique_together': "(('title', 'user'),)", 'object_name': 'AlertPluginUserData'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'polymorphic_cabotapp.alertpluginuserdata_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['cabotapp.UserProfile']"})
        },
        u'cabotapp.graphitestatuscheck': {
            'Meta': {'ordering': "['name']", 'object_name': 'GraphiteStatusCheck', '_ormbases': [u'cabotapp.StatusCheck']},
            'check_type': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'expected_num_hosts': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'expected_num_metrics': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'fill_empty': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'group_by': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'interval': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'metric': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'metric_selector': ('django.db.models.fields.CharField', [], {'default': "'value'", 'max_length': '50'}),
            u'statuscheck_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['cabotapp.StatusCheck']", 'unique': 'True', 'primary_key': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'where_clause': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'blank': 'True'})
        },
        u'cabotapp.httpstatuscheck': {
            'Meta': {'ordering': "['name']", 'object_name': 'HttpStatusCheck', '_ormbases': [u'cabotapp.StatusCheck']},
            'allow_http_redirects': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'endpoint': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'header_match': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'http_body': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'http_method': ('django.db.models.fields.CharField', [], {'default': "'GET'", 'max_length': '10'}),
            'http_params': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'password': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'statuscheck_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['cabotapp.StatusCheck']", 'unique': 'True', 'primary_key': 'True'}),
            'status_code': ('django.db.models.fields.TextField', [], {'default': '200', 'null': 'True'}),
            'text_match': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'timeout': ('django.db.models.fields.IntegerField', [], {'default': '30', 'null': 'True'}),
            'username': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'verify_ssl_certificate': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'cabotapp.icmpstatuscheck': {
            'Meta': {'ordering': "['name']", 'object_name': 'ICMPStatusCheck', '_ormbases': [u'cabotapp.StatusCheck']},
            u'statuscheck_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['cabotapp.StatusCheck']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'cabotapp.influxdbstatuscheck': {
            'Meta': {'ordering': "['name']", 'object_name': 'InfluxDBStatusCheck', '_ormbases': [u'cabotapp.GraphiteStatusCheck']},
            u'graphitestatuscheck_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['cabotapp.GraphiteStatusCheck']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'cabotapp.instance': {
            'Meta': {'ordering': "['name']", 'object_name': 'Instance'},
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'alerts': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['cabotapp.AlertPlugin']", 'symmetrical': 'False', 'blank': 'True'}),
            'alerts_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'email_alert': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hackpad_id': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'hipchat_alert': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_alert_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'old_overall_status': ('django.db.models.fields.TextField', [], {'default': "'PASSING'"}),
            'overall_status': ('django.db.models.fields.TextField', [], {'default': "'PASSING'"}),
            'schedules': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['cabotapp.Schedule']", 'null': 'True', 'blank': 'True'}),
            'sms_alert': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'status_checks': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['cabotapp.StatusCheck']", 'symmetrical': 'False', 'blank': 'True'}),
            'telephone_alert': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'users_to_notify': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'cabotapp.instancestatussnapshot': {
            'Meta': {'object_name': 'InstanceStatusSnapshot'},
            'did_send_alert': ('django.db.models.fields.IntegerField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'snapshots'", 'to': u"orm['cabotapp.Instance']"}),
            'num_checks_active': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_checks_failing': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_checks_passing': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'overall_status': ('django.db.models.fields.TextField', [], {'default': "'PASSING'"}),
            'time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        },
        u'cabotapp.jenkinsstatuscheck': {
            'Meta': {'ordering': "['name']", 'object_name': 'JenkinsStatusCheck', '_ormbases': [u'cabotapp.StatusCheck']},
            'max_queued_build_time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'statuscheck_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['cabotapp.StatusCheck']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'cabotapp.schedule': {
            'Meta': {'object_name': 'Schedule'},
            'fallback_officer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'ical_url': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'cabotapp.service': {
            'Meta': {'ordering': "['name']", 'object_name': 'Service'},
            'alerts': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['cabotapp.AlertPlugin']", 'symmetrical': 'False', 'blank': 'True'}),
            'alerts_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'email_alert': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hackpad_id': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'hipchat_alert': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instances': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['cabotapp.Instance']", 'symmetrical': 'False', 'blank': 'True'}),
            'last_alert_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'old_overall_status': ('django.db.models.fields.TextField', [], {'default': "'PASSING'"}),
            'overall_status': ('django.db.models.fields.TextField', [], {'default': "'PASSING'"}),
            'schedules': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['cabotapp.Schedule']", 'null': 'True', 'blank': 'True'}),
            'sms_alert': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'status_checks': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['cabotapp.StatusCheck']", 'symmetrical': 'False', 'blank': 'True'}),
            'telephone_alert': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'users_to_notify': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'cabotapp.servicestatussnapshot': {
            'Meta': {'object_name': 'ServiceStatusSnapshot'},
            'did_send_alert': ('django.db.models.fields.IntegerField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_checks_active': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_checks_failing': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_checks_passing': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'overall_status': ('django.db.models.fields.TextField', [], {'default': "'PASSING'"}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'snapshots'", 'to': u"orm['cabotapp.Service']"}),
            'time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        },
        u'cabotapp.shift': {
            'Meta': {'object_name': 'Shift'},
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'schedule': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': u"orm['cabotapp.Schedule']"}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'uid': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'cabotapp.statuscheck': {
            'Meta': {'ordering': "['name']", 'object_name': 'StatusCheck'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'cached_health': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'calculated_status': ('django.db.models.fields.CharField', [], {'default': "'passing'", 'max_length': '50', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
            'debounce': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'frequency': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.CharField', [], {'default': "'ERROR'", 'max_length': '30'}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'polymorphic_cabotapp.statuscheck_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'rallow_http_redirects': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rcheck_type': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'rendpoint': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'rexpected_num_hosts': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'rexpected_num_metrics': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'rfill_empty': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'rgroup_by': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'rheader_match': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'rhttp_body': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'rhttp_method': ('django.db.models.fields.CharField', [], {'default': "'GET'", 'max_length': '10'}),
            'rhttp_params': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'rinterval': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'rmax_queued_build_time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'rmetric': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'rmetric_selector': ('django.db.models.fields.CharField', [], {'default': "'value'", 'max_length': '50'}),
            'rpassword': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'rtext_match': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'rtimeout': ('django.db.models.fields.IntegerField', [], {'default': '30', 'null': 'True'}),
            'rusername': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'rverify_ssl_certificate': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rwhere_clause': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'blank': 'True'}),
            'rstatus_code': ('django.db.models.fields.TextField', [], {'default': '200', 'null': 'True'}),
            'rvalue': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        u'cabotapp.statuscheckresult': {
            'Meta': {'object_name': 'StatusCheckResult'},
            'check': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['cabotapp.StatusCheck']"}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job_number': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'succeeded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'time_complete': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'db_index': 'True'})
        },
        u'cabotapp.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'hipchat_alias': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mobile_number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'profile'", 'unique': 'True', 'to': u"orm['auth.User']"})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['cabotapp']
    symmetrical = True
