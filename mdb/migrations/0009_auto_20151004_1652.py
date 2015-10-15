# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import re
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('mdb', '0008_auto_20151004_1258'),
    ]

    operations = [
        migrations.AddField(
            model_name='domain',
            name='domain_ip6addr',
            field=models.GenericIPAddressField(null=True, protocol='IPv6', blank=True),
        ),
        migrations.AlterField(
            model_name='host',
            name='hostname',
            field=models.CharField(max_length=64, validators=[django.core.validators.RegexValidator(regex=re.compile('^(?!-)[-a-z0-9]+(?<!-)$', 2), message='Enter a valid hostname', code='invalid')]),
        ),
        migrations.AlterField(
            model_name='interface',
            name='macaddr',
            field=models.CharField(max_length=17, validators=[django.core.validators.RegexValidator(regex=re.compile('^([0-9A-F]{2}[:]){5}([0-9A-F]{2})$', 2), message='Enter a valid MAC address', code='invalid')]),
        ),
    ]
