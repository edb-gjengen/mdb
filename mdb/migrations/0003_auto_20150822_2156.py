# -*- coding: utf-8 -*-
from django.db import models, migrations
import django.core.validators
import re


class Migration(migrations.Migration):

    dependencies = [
        ('mdb', '0002_auto_20141229_2309'),
    ]

    operations = [
        migrations.AddField(
            model_name='operatingsystem',
            name='arch',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'mips', 'MIPS'), (b'arm', 'ARM'), (b'broadcom', 'Broadcom'), (b'rc32300', 'RC32300'), (b'powerpc', 'PowerPC'), (b'powerpc403ga', 'PowerPC403GA'), (b'unknown', 'Unknown'), (b'x86_64', 'x86-64'), (b'i386', 'x86')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='interface',
            name='macaddr',
            field=models.CharField(max_length=17, validators=[django.core.validators.RegexValidator(regex=re.compile(b'^([0-9A-F]{2}[:]){5}([0-9A-F]{2})$', 2), message='Enter a valid MAC address', code=b'invalid')]),
        ),
    ]
