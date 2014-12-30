# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mdb', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ip4address',
            name='last_contact',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='ip4address',
            name='ping_avg_rtt',
            field=models.FloatField(null=True, blank=True),
        ),
    ]
