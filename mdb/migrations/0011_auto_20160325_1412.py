# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mdb', '0010_auto_20151004_1709'),
    ]

    operations = [
        migrations.AddField(
            model_name='operatingsystem',
            name='pxe_initrd',
            field=models.CharField(null=True, blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='operatingsystem',
            name='pxe_kernel',
            field=models.CharField(null=True, blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='operatingsystem',
            name='pxe_preseed_config_url',
            field=models.URLField(null=True, blank=True),
        ),
    ]
