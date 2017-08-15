# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cabotapp', '0003_auto_20170201_1045'),
    ]

    operations = [
        migrations.AddField(
            model_name='Service',
            name='is_public',
            field=models.BooleanField(default=False, help_text=b'The service will be shown in the public home', verbose_name=b'Is Public'),
        ),
    ]
