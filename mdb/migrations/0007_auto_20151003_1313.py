# -*- coding: utf-8 -*-
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mdb', '0006_auto_20151001_2235'),
    ]

    operations = [
        migrations.AddField(
            model_name='host',
            name='pxe_installable',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='host',
            name='pxe_key',
            field=models.CharField(max_length=254, blank=True),
        ),
    ]
