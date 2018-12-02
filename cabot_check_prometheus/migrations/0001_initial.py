# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cabotapp', '0006_auto_20170821_1000'),
    ]

    operations = [
        migrations.CreateModel(
            name='PrometheusStatusCheck',
            fields=[
                ('statuscheck_ptr',
                 models.OneToOneField(
                     auto_created=True,
                     on_delete=django.db.models.deletion.CASCADE,
                     parent_link=True,
                     primary_key=True,
                     serialize=False,
                     to='cabotapp.StatusCheck')),
                ('host',
                 models.TextField(
                     help_text=b'Host to check.',
                     null=False,
                     blank=False,
                     default=None)),
                ('query',
                 models.TextField(
                     help_text=b'Query to execute.',
                     null=False,
                     blank=False,
                     default=None)),
            ],
            options={
                'abstract': False,
            },
            bases=('cabotapp.statuscheck',),
        ),
    ]
