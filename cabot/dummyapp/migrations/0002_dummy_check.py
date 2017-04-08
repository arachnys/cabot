# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.contrib.auth.models import User
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        """Create a dummy check"""
        source = orm.DummySource.objects.create(name='dummy_source')
        source.save()

        ct, _ = orm['contenttypes.ContentType'].objects.get_or_create(app_label='dummyapp', model='dummystatuscheck')
        check = orm.DummyStatusCheck.objects.create(
            name='dummy_check',
            source=source,
            check_type='<',
            warning_value=500,
            high_alert_value=1500,
            high_alert_importance='ERROR',
            counter=0,
            retries=2,
            polymorphic_ctype=ct,
        )
        check.save()

    def backwards(self, orm):
        "Write your backwards methods here."

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
        u'cabotapp.statuscheck': {
            'Meta': {'ordering': "['name']", 'object_name': 'StatusCheck'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'cached_health': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'calculated_status': ('django.db.models.fields.CharField', [], {'default': "'passing'", 'max_length': '50', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
            'retries': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'frequency': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.CharField', [], {'default': "'ERROR'", 'max_length': '30'}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'polymorphic_cabotapp.statuscheck_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dummyapp.dummysource': {
            'Meta': {'object_name': 'DummySource', '_ormbases': ['metricsapp.MetricsSourceBase']},
            u'metricssourcebase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['metricsapp.MetricsSourceBase']", 'unique': 'True', 'primary_key': 'True'})
        },
        'dummyapp.dummystatuscheck': {
            'Meta': {'ordering': "['name']", 'object_name': 'DummyStatusCheck', '_ormbases': ['metricsapp.MetricsStatusCheckBase']},
            'counter': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'metricsstatuscheckbase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['metricsapp.MetricsStatusCheckBase']", 'unique': 'True', 'primary_key': 'True'})
        },
        'metricsapp.metricssourcebase': {
            'Meta': {'object_name': 'MetricsSourceBase'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'metricsapp.metricsstatuscheckbase': {
            'Meta': {'ordering': "['name']", 'object_name': 'MetricsStatusCheckBase', '_ormbases': [u'cabotapp.StatusCheck']},
            'check_type': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'high_alert_importance': ('django.db.models.fields.CharField', [], {'default': "'ERROR'", 'max_length': '30'}),
            'high_alert_value': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['metricsapp.MetricsSourceBase']"}),
            u'statuscheck_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['cabotapp.StatusCheck']", 'unique': 'True', 'primary_key': 'True'}),
            'time_range': ('django.db.models.fields.IntegerField', [], {'default': '30'}),
            'warning_value': ('django.db.models.fields.FloatField', [], {'null': 'True'})
        }
    }

    complete_apps = ['dummyapp']
    symmetrical = True
