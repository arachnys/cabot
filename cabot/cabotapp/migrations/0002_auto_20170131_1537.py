# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cabotapp', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='statuscheckresult',
            old_name='check',
            new_name='status_check',
        ),
        migrations.AlterIndexTogether(
            name='statuscheckresult',
            index_together=set([('status_check', 'time_complete'), ('status_check', 'id')]),
        ),
    ]
