# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cabotapp', '0002_auto_20170131_1537'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alertplugin',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_cabotapp.alertplugin_set+', editable=False, to='contenttypes.ContentType', null=True),
        ),
        migrations.AlterField(
            model_name='alertpluginuserdata',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_cabotapp.alertpluginuserdata_set+', editable=False, to='contenttypes.ContentType', null=True),
        ),
        migrations.AlterField(
            model_name='statuscheck',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_cabotapp.statuscheck_set+', editable=False, to='contenttypes.ContentType', null=True),
        ),
    ]
