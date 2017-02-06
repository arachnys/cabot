# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlertAcknowledgement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time', models.DateTimeField()),
                ('cancelled_time', models.DateTimeField(null=True, blank=True)),
                ('cancelled_user', models.ForeignKey(related_name='cancelleduser_set', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AlertPlugin',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(unique=True, max_length=30, editable=False)),
                ('enabled', models.BooleanField(default=True)),
                ('polymorphic_ctype', models.ForeignKey(related_name='polymorphic_cabotapp.alertplugin_set', editable=False, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AlertPluginUserData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=30, editable=False)),
                ('polymorphic_ctype', models.ForeignKey(related_name='polymorphic_cabotapp.alertpluginuserdata_set', editable=False, to='contenttypes.ContentType', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Instance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField()),
                ('alerts_enabled', models.BooleanField(default=True, help_text=b'Alert when this service is not healthy.')),
                ('last_alert_sent', models.DateTimeField(null=True, blank=True)),
                ('email_alert', models.BooleanField(default=False)),
                ('hipchat_alert', models.BooleanField(default=True)),
                ('sms_alert', models.BooleanField(default=False)),
                ('telephone_alert', models.BooleanField(default=False, help_text=b'Must be enabled, and check importance set to Critical, to receive telephone alerts.')),
                ('overall_status', models.TextField(default=b'PASSING')),
                ('old_overall_status', models.TextField(default=b'PASSING')),
                ('hackpad_id', models.TextField(help_text=b'Gist, Hackpad or Refheap js embed with recovery instructions e.g. https://you.hackpad.com/some_document.js', null=True, verbose_name=b'Embedded recovery instructions', blank=True)),
                ('runbook_link', models.TextField(help_text=b'Link to the service runbook on your wiki.', blank=True)),
                ('address', models.TextField(help_text=b'Address (IP/Hostname) of service.', blank=True)),
                ('alerts', models.ManyToManyField(help_text=b'Alerts channels through which you wish to be notified', to='cabotapp.AlertPlugin', blank=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InstanceStatusSnapshot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time', models.DateTimeField(db_index=True)),
                ('num_checks_active', models.IntegerField(default=0)),
                ('num_checks_passing', models.IntegerField(default=0)),
                ('num_checks_failing', models.IntegerField(default=0)),
                ('overall_status', models.TextField(default=b'PASSING')),
                ('did_send_alert', models.IntegerField(default=False)),
                ('instance', models.ForeignKey(related_name='snapshots', to='cabotapp.Instance')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField()),
                ('alerts_enabled', models.BooleanField(default=True, help_text=b'Alert when this service is not healthy.')),
                ('last_alert_sent', models.DateTimeField(null=True, blank=True)),
                ('email_alert', models.BooleanField(default=False)),
                ('hipchat_alert', models.BooleanField(default=True)),
                ('sms_alert', models.BooleanField(default=False)),
                ('telephone_alert', models.BooleanField(default=False, help_text=b'Must be enabled, and check importance set to Critical, to receive telephone alerts.')),
                ('overall_status', models.TextField(default=b'PASSING')),
                ('old_overall_status', models.TextField(default=b'PASSING')),
                ('hackpad_id', models.TextField(help_text=b'Gist, Hackpad or Refheap js embed with recovery instructions e.g. https://you.hackpad.com/some_document.js', null=True, verbose_name=b'Embedded recovery instructions', blank=True)),
                ('runbook_link', models.TextField(help_text=b'Link to the service runbook on your wiki.', blank=True)),
                ('url', models.TextField(help_text=b'URL of service.', blank=True)),
                ('alerts', models.ManyToManyField(help_text=b'Alerts channels through which you wish to be notified', to='cabotapp.AlertPlugin', blank=True)),
                ('instances', models.ManyToManyField(help_text=b'Instances this service is running on.', to='cabotapp.Instance', blank=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ServiceStatusSnapshot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time', models.DateTimeField(db_index=True)),
                ('num_checks_active', models.IntegerField(default=0)),
                ('num_checks_passing', models.IntegerField(default=0)),
                ('num_checks_failing', models.IntegerField(default=0)),
                ('overall_status', models.TextField(default=b'PASSING')),
                ('did_send_alert', models.IntegerField(default=False)),
                ('service', models.ForeignKey(related_name='snapshots', to='cabotapp.Service')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Shift',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start', models.DateTimeField()),
                ('end', models.DateTimeField()),
                ('uid', models.TextField()),
                ('last_modified', models.DateTimeField()),
                ('deleted', models.BooleanField(default=False)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StatusCheck',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField()),
                ('active', models.BooleanField(default=True, help_text=b'If not active, check will not be used to calculate service status and will not trigger alerts.')),
                ('importance', models.CharField(default=b'ERROR', help_text=b'Severity level of a failure. Critical alerts are for failures you want to wake you up at 2am, Errors are things you can sleep through but need to fix in the morning, and warnings for less important things.', max_length=30, choices=[(b'WARNING', b'Warning'), (b'ERROR', b'Error'), (b'CRITICAL', b'Critical')])),
                ('frequency', models.IntegerField(default=5, help_text=b'Minutes between each check.')),
                ('debounce', models.IntegerField(default=0, help_text=b'Number of successive failures permitted before check will be marked as failed. Default is 0, i.e. fail on first failure.', null=True)),
                ('calculated_status', models.CharField(default=b'passing', max_length=50, blank=True, choices=[(b'passing', b'passing'), (b'intermittent', b'intermittent'), (b'failing', b'failing')])),
                ('last_run', models.DateTimeField(null=True)),
                ('cached_health', models.TextField(null=True, editable=False)),
                ('metric', models.TextField(help_text=b'fully.qualified.name of the Graphite metric you want to watch. This can be any valid Graphite expression, including wildcards, multiple hosts, etc.', null=True)),
                ('check_type', models.CharField(max_length=100, null=True, choices=[(b'>', b'Greater than'), (b'>=', b'Greater than or equal'), (b'<', b'Less than'), (b'<=', b'Less than or equal'), (b'==', b'Equal to')])),
                ('value', models.TextField(help_text=b'If this expression evaluates to true, the check will fail (possibly triggering an alert).', null=True)),
                ('expected_num_hosts', models.IntegerField(default=0, help_text=b'The minimum number of data series (hosts) you expect to see.', null=True)),
                ('allowed_num_failures', models.IntegerField(default=0, help_text=b'The maximum number of data series (metrics) you expect to fail. For example, you might be OK with 2 out of 3 webservers having OK load (1 failing), but not 1 out of 3 (2 failing).', null=True)),
                ('endpoint', models.TextField(help_text=b'HTTP(S) endpoint to poll.', null=True)),
                ('username', models.TextField(help_text=b'Basic auth username.', null=True, blank=True)),
                ('password', models.TextField(help_text=b'Basic auth password.', null=True, blank=True)),
                ('text_match', models.TextField(help_text=b'Regex to match against source of page.', null=True, blank=True)),
                ('status_code', models.TextField(default=200, help_text=b'Status code expected from endpoint.', null=True)),
                ('timeout', models.IntegerField(default=30, help_text=b'Time out after this many seconds.', null=True)),
                ('verify_ssl_certificate', models.BooleanField(default=True, help_text=b'Set to false to allow not try to verify ssl certificates (default True)')),
                ('max_queued_build_time', models.IntegerField(help_text=b'Alert if build queued for more than this many minutes.', null=True, blank=True)),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True)),
                ('polymorphic_ctype', models.ForeignKey(related_name='polymorphic_cabotapp.statuscheck_set', editable=False, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StatusCheckResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time', models.DateTimeField(db_index=True)),
                ('time_complete', models.DateTimeField(null=True, db_index=True)),
                ('raw_data', models.TextField(null=True)),
                ('succeeded', models.BooleanField(default=False)),
                ('error', models.TextField(null=True)),
                ('job_number', models.PositiveIntegerField(null=True)),
                ('check', models.ForeignKey(to='cabotapp.StatusCheck')),
            ],
            options={
                'ordering': ['-time_complete'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('mobile_number', models.CharField(default=b'', max_length=20, blank=True)),
                ('hipchat_alias', models.CharField(default=b'', max_length=50, blank=True)),
                ('fallback_alert_user', models.BooleanField(default=False)),
                ('user', models.OneToOneField(related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterIndexTogether(
            name='statuscheckresult',
            index_together=set([('check', 'time_complete'), ('check', 'id')]),
        ),
        migrations.AddField(
            model_name='service',
            name='status_checks',
            field=models.ManyToManyField(help_text=b'Checks used to calculate service status.', to='cabotapp.StatusCheck', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='service',
            name='users_to_notify',
            field=models.ManyToManyField(help_text=b'Users who should receive alerts.', to=settings.AUTH_USER_MODEL, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instance',
            name='status_checks',
            field=models.ManyToManyField(help_text=b'Checks used to calculate service status.', to='cabotapp.StatusCheck', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instance',
            name='users_to_notify',
            field=models.ManyToManyField(help_text=b'Users who should receive alerts.', to=settings.AUTH_USER_MODEL, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='alertpluginuserdata',
            name='user',
            field=models.ForeignKey(editable=False, to='cabotapp.UserProfile'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='alertpluginuserdata',
            unique_together=set([('title', 'user')]),
        ),
        migrations.AddField(
            model_name='alertacknowledgement',
            name='service',
            field=models.ForeignKey(to='cabotapp.Service'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='alertacknowledgement',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='GraphiteStatusCheck',
            fields=[
            ],
            options={
                'abstract': False,
                'proxy': True,
            },
            bases=('cabotapp.statuscheck',),
        ),
        migrations.CreateModel(
            name='HttpStatusCheck',
            fields=[
            ],
            options={
                'abstract': False,
                'proxy': True,
            },
            bases=('cabotapp.statuscheck',),
        ),
        migrations.CreateModel(
            name='ICMPStatusCheck',
            fields=[
            ],
            options={
                'abstract': False,
                'proxy': True,
            },
            bases=('cabotapp.statuscheck',),
        ),
        migrations.CreateModel(
            name='JenkinsStatusCheck',
            fields=[
            ],
            options={
                'abstract': False,
                'proxy': True,
            },
            bases=('cabotapp.statuscheck',),
        ),
    ]
