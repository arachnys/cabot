# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-01-10 22:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cabotapp', '0007_statuscheckresult_consecutive_failures'),
    ]

    operations = [
        migrations.AddField(
            model_name='statuscheck',
            name='text_match_expected_result',
            field=models.BooleanField(default=True, help_text=b'Text match expected result positive or negative. (default True)'),
        ),
    ]