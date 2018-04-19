# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'MetricsStatusCheckBase.consecutive_failures'
        db.add_column(u'metricsapp_metricsstatuscheckbase', 'consecutive_failures',
                      self.gf('django.db.models.fields.IntegerField')(default=1),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'MetricsStatusCheckBase.consecutive_failures'
        db.delete_column(u'metricsapp_metricsstatuscheckbase', 'consecutive_failures')


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
            'frequency': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.CharField', [], {'default': "'ERROR'", 'max_length': '30'}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'polymorphic_cabotapp.statuscheck_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'retries': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'null': 'True'}),
            'runbook': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'metricsapp.elasticsearchsource': {
            'Meta': {'object_name': 'ElasticsearchSource', '_ormbases': ['metricsapp.MetricsSourceBase']},
            'index': ('django.db.models.fields.TextField', [], {'default': "'*'", 'max_length': '50'}),
            'max_concurrent_searches': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            u'metricssourcebase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['metricsapp.MetricsSourceBase']", 'unique': 'True', 'primary_key': 'True'}),
            'timeout': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'urls': ('django.db.models.fields.TextField', [], {'max_length': '250'})
        },
        'metricsapp.elasticsearchstatuscheck': {
            'Meta': {'ordering': "['name']", 'object_name': 'ElasticsearchStatusCheck', '_ormbases': ['metricsapp.MetricsStatusCheckBase']},
            u'metricsstatuscheckbase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['metricsapp.MetricsStatusCheckBase']", 'unique': 'True', 'primary_key': 'True'}),
            'queries': ('django.db.models.fields.TextField', [], {'max_length': '10000'})
        },
        'metricsapp.grafanadatasource': {
            'Meta': {'object_name': 'GrafanaDataSource'},
            'grafana_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['metricsapp.GrafanaInstance']"}),
            'grafana_source_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metrics_source_base': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['metricsapp.MetricsSourceBase']"})
        },
        'metricsapp.grafanainstance': {
            'Meta': {'object_name': 'GrafanaInstance'},
            'api_key': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'sources': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['metricsapp.MetricsSourceBase']", 'through': "orm['metricsapp.GrafanaDataSource']", 'symmetrical': 'False'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'metricsapp.grafanapanel': {
            'Meta': {'object_name': 'GrafanaPanel'},
            'dashboard_uri': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'grafana_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['metricsapp.GrafanaInstance']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'panel_id': ('django.db.models.fields.IntegerField', [], {}),
            'panel_url': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True'}),
            'selected_series': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'series_ids': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'metricsapp.metricssourcebase': {
            'Meta': {'object_name': 'MetricsSourceBase'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'metricsapp.metricsstatuscheckbase': {
            'Meta': {'ordering': "['name']", 'object_name': 'MetricsStatusCheckBase', '_ormbases': [u'cabotapp.StatusCheck']},
            'auto_sync': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'check_type': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'consecutive_failures': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'grafana_panel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['metricsapp.GrafanaPanel']", 'null': 'True'}),
            'high_alert_importance': ('django.db.models.fields.CharField', [], {'default': "'ERROR'", 'max_length': '30'}),
            'high_alert_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['metricsapp.MetricsSourceBase']"}),
            u'statuscheck_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['cabotapp.StatusCheck']", 'unique': 'True', 'primary_key': 'True'}),
            'time_range': ('django.db.models.fields.IntegerField', [], {'default': '30'}),
            'warning_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['metricsapp']