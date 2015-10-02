# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'AlertAcknowledgement.cancelled_time'
        db.add_column(u'cabotapp_alertacknowledgement', 'cancelled_time',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'AlertAcknowledgement.cancelled_user'
        db.add_column(u'cabotapp_alertacknowledgement', 'cancelled_user',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='cancelleduser_set', null=True, to=orm['auth.User']),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'AlertAcknowledgement.cancelled_time'
        db.delete_column(u'cabotapp_alertacknowledgement', 'cancelled_time')

        # Deleting field 'AlertAcknowledgement.cancelled_user'
        db.delete_column(u'cabotapp_alertacknowledgement', 'cancelled_user_id')


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
        u'cabotapp.alertacknowledgement': {
            'Meta': {'object_name': 'AlertAcknowledgement'},
            'cancelled_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'cancelled_user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'cancelleduser_set'", 'null': 'True', 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['cabotapp.Service']"}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
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
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'uid': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'cabotapp.statuscheck': {
            'Meta': {'ordering': "['name']", 'object_name': 'StatusCheck'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'allowed_num_failures': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'cached_health': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'calculated_status': ('django.db.models.fields.CharField', [], {'default': "'passing'", 'max_length': '50', 'blank': 'True'}),
            'check_type': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
            'debounce': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'endpoint': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'expected_num_hosts': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'frequency': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.CharField', [], {'default': "'ERROR'", 'max_length': '30'}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'max_queued_build_time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'metric': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'password': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'polymorphic_cabotapp.statuscheck_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'status_code': ('django.db.models.fields.TextField', [], {'default': '200', 'null': 'True'}),
            'text_match': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'timeout': ('django.db.models.fields.IntegerField', [], {'default': '30', 'null': 'True'}),
            'username': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'verify_ssl_certificate': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'cabotapp.statuscheckresult': {
            'Meta': {'ordering': "['-time_complete']", 'object_name': 'StatusCheckResult'},
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
            'fallback_alert_user': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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