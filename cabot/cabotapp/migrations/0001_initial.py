# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Service'
        db.create_table('cabotapp_service', (
            ('id', self.gf('django.db.models.fields.AutoField')
             (primary_key=True)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('url', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('last_alert_sent', self.gf('django.db.models.fields.DateTimeField')
             (null=True, blank=True)),
            ('email_alert', self.gf('django.db.models.fields.BooleanField')
             (default=False)),
            ('hipchat_alert',
             self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('sms_alert', self.gf('django.db.models.fields.BooleanField')
             (default=False)),
            ('telephone_alert',
             self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('alerts_enabled',
             self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('overall_status', self.gf('django.db.models.fields.TextField')
             (default='PASSING')),
            ('old_overall_status',
             self.gf('django.db.models.fields.TextField')(default='PASSING')),
            ('hackpad_id', self.gf('django.db.models.fields.TextField')
             (null=True, blank=True)),
        ))
        db.send_create_signal('cabotapp', ['Service'])

        # Adding M2M table for field users_to_notify on 'Service'
        db.create_table('cabotapp_service_users_to_notify', (
            ('id', models.AutoField(verbose_name='ID',
             primary_key=True, auto_created=True)),
            ('service',
             models.ForeignKey(orm['cabotapp.service'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('cabotapp_service_users_to_notify',
                         ['service_id', 'user_id'])

        # Adding M2M table for field status_checks on 'Service'
        db.create_table('cabotapp_service_status_checks', (
            ('id', models.AutoField(verbose_name='ID',
             primary_key=True, auto_created=True)),
            ('service',
             models.ForeignKey(orm['cabotapp.service'], null=False)),
            ('statuscheck',
             models.ForeignKey(orm['cabotapp.statuscheck'], null=False))
        ))
        db.create_unique('cabotapp_service_status_checks',
                         ['service_id', 'statuscheck_id'])

        # Adding model 'ServiceStatusSnapshot'
        db.create_table('cabotapp_servicestatussnapshot', (
            ('id', self.gf('django.db.models.fields.AutoField')
             (primary_key=True)),
            ('service', self.gf('django.db.models.fields.related.ForeignKey')
             (related_name='snapshots', to=orm['cabotapp.Service'])),
            ('time', self.gf('django.db.models.fields.DateTimeField')()),
            ('num_checks_active',
             self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('num_checks_passing',
             self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('num_checks_failing',
             self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('overall_status', self.gf('django.db.models.fields.TextField')
             (default='PASSING')),
            ('did_send_alert',
             self.gf('django.db.models.fields.IntegerField')(default=False)),
        ))
        db.send_create_signal('cabotapp', ['ServiceStatusSnapshot'])

        # Adding model 'StatusCheck'
        db.create_table('cabotapp_statuscheck', (
            ('id', self.gf('django.db.models.fields.AutoField')
             (primary_key=True)),
            ('polymorphic_ctype', self.gf('django.db.models.fields.related.ForeignKey')
             (related_name='polymorphic_cabotapp.statuscheck_set', null=True, to=orm['contenttypes.ContentType'])),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('active', self.gf('django.db.models.fields.BooleanField')
             (default=True)),
            ('importance', self.gf('django.db.models.fields.CharField')
             (default='ERROR', max_length=30)),
            ('frequency', self.gf('django.db.models.fields.IntegerField')
             (default=5)),
            ('debounce', self.gf('django.db.models.fields.IntegerField')
             (default=0, null=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')
             (to=orm['auth.User'])),
            ('calculated_status', self.gf('django.db.models.fields.CharField')
             (default='passing', max_length=50, blank=True)),
            ('last_run', self.gf('django.db.models.fields.DateTimeField')
             (null=True)),
            ('cached_health',
             self.gf('django.db.models.fields.TextField')(null=True)),
            ('metric', self.gf('django.db.models.fields.TextField')
             (null=True)),
            ('check_type', self.gf('django.db.models.fields.CharField')
             (max_length=100, null=True)),
            ('value', self.gf('django.db.models.fields.TextField')(null=True)),
            ('expected_num_hosts', self.gf('django.db.models.fields.IntegerField')
             (default=0, null=True)),
            ('endpoint', self.gf('django.db.models.fields.TextField')
             (null=True)),
            ('username', self.gf('django.db.models.fields.TextField')
             (null=True, blank=True)),
            ('password', self.gf('django.db.models.fields.TextField')
             (null=True, blank=True)),
            ('text_match', self.gf('django.db.models.fields.TextField')
             (null=True, blank=True)),
            ('status_code', self.gf('django.db.models.fields.TextField')
             (default=200, null=True)),
            ('timeout', self.gf('django.db.models.fields.IntegerField')
             (default=30, null=True)),
            ('max_queued_build_time',
             self.gf(
                 'django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('cabotapp', ['StatusCheck'])

        # Adding model 'StatusCheckResult'
        db.create_table('cabotapp_statuscheckresult', (
            ('id', self.gf('django.db.models.fields.AutoField')
             (primary_key=True)),
            ('check', self.gf('django.db.models.fields.related.ForeignKey')
             (to=orm['cabotapp.StatusCheck'])),
            ('time', self.gf('django.db.models.fields.DateTimeField')()),
            ('time_complete',
             self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('raw_data', self.gf('django.db.models.fields.TextField')
             (null=True)),
            ('succeeded', self.gf('django.db.models.fields.BooleanField')
             (default=False)),
            ('error', self.gf('django.db.models.fields.TextField')(null=True)),
        ))
        db.send_create_signal('cabotapp', ['StatusCheckResult'])

        # Adding model 'UserProfile'
        db.create_table('cabotapp_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')
             (primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')
             (related_name='profile', unique=True, to=orm['auth.User'])),
            ('mobile_number', self.gf('django.db.models.fields.CharField')
             (default='', max_length=20, blank=True)),
            ('hipchat_alias', self.gf('django.db.models.fields.CharField')
             (default='', max_length=50, blank=True)),
            ('fallback_alert_user',
             self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('cabotapp', ['UserProfile'])

        # Adding model 'Shift'
        db.create_table('cabotapp_shift', (
            ('id', self.gf('django.db.models.fields.AutoField')
             (primary_key=True)),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('end', self.gf('django.db.models.fields.DateTimeField')()),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')
             (to=orm['auth.User'])),
            ('uid', self.gf('django.db.models.fields.TextField')()),
            ('deleted', self.gf('django.db.models.fields.BooleanField')
             (default=False)),
        ))
        db.send_create_signal('cabotapp', ['Shift'])

    def backwards(self, orm):
        # Deleting model 'Service'
        db.delete_table('cabotapp_service')

        # Removing M2M table for field users_to_notify on 'Service'
        db.delete_table('cabotapp_service_users_to_notify')

        # Removing M2M table for field status_checks on 'Service'
        db.delete_table('cabotapp_service_status_checks')

        # Deleting model 'ServiceStatusSnapshot'
        db.delete_table('cabotapp_servicestatussnapshot')

        # Deleting model 'StatusCheck'
        db.delete_table('cabotapp_statuscheck')

        # Deleting model 'StatusCheckResult'
        db.delete_table('cabotapp_statuscheckresult')

        # Deleting model 'UserProfile'
        db.delete_table('cabotapp_userprofile')

        # Deleting model 'Shift'
        db.delete_table('cabotapp_shift')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cabotapp.service': {
            'Meta': {'ordering': "['name']", 'object_name': 'Service'},
            'alerts_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'email_alert': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hackpad_id': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'hipchat_alert': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_alert_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'old_overall_status': ('django.db.models.fields.TextField', [], {'default': "'PASSING'"}),
            'overall_status': ('django.db.models.fields.TextField', [], {'default': "'PASSING'"}),
            'sms_alert': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'status_checks': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cabotapp.StatusCheck']", 'symmetrical': 'False', 'blank': 'True'}),
            'telephone_alert': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'users_to_notify': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'cabotapp.servicestatussnapshot': {
            'Meta': {'object_name': 'ServiceStatusSnapshot'},
            'did_send_alert': ('django.db.models.fields.IntegerField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_checks_active': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_checks_failing': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_checks_passing': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'overall_status': ('django.db.models.fields.TextField', [], {'default': "'PASSING'"}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'snapshots'", 'to': "orm['cabotapp.Service']"}),
            'time': ('django.db.models.fields.DateTimeField', [], {})
        },
        'cabotapp.shift': {
            'Meta': {'object_name': 'Shift'},
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'uid': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'cabotapp.statuscheck': {
            'Meta': {'ordering': "['name']", 'object_name': 'StatusCheck'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'cached_health': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'calculated_status': ('django.db.models.fields.CharField', [], {'default': "'passing'", 'max_length': '50', 'blank': 'True'}),
            'check_type': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'debounce': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'endpoint': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'expected_num_hosts': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'frequency': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.CharField', [], {'default': "'ERROR'", 'max_length': '30'}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'max_queued_build_time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'metric': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'password': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_cabotapp.statuscheck_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'status_code': ('django.db.models.fields.TextField', [], {'default': '200', 'null': 'True'}),
            'text_match': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'timeout': ('django.db.models.fields.IntegerField', [], {'default': '30', 'null': 'True'}),
            'username': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        'cabotapp.statuscheckresult': {
            'Meta': {'object_name': 'StatusCheckResult'},
            'check': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cabotapp.StatusCheck']"}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'succeeded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'time_complete': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'cabotapp.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'fallback_alert_user': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hipchat_alias': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mobile_number': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'profile'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['cabotapp']
