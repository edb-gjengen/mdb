# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
import re


class Migration(migrations.Migration):

    dependencies = [
        ('mdb', '0005_auto_20150822_2204'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dhcpcustomfield',
            options={'verbose_name': 'DHCP custom field'},
        ),
        migrations.AlterField(
            model_name='domain',
            name='domain_admin',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='domain',
            name='domain_ipaddr',
            field=models.GenericIPAddressField(protocol='IPv4'),
        ),
        migrations.AlterField(
            model_name='host',
            name='hostname',
            field=models.CharField(validators=[django.core.validators.RegexValidator(code='invalid', message='Enter a valid hostname', regex=re.compile('^(?!-)[-a-z0-9]+(?<!-)$', 34))], max_length=64),
        ),
        migrations.AlterField(
            model_name='interface',
            name='ip4address',
            field=models.OneToOneField(to='mdb.Ip4Address', null=True, blank=True, on_delete=models.SET_NULL),
        ),
        migrations.AlterField(
            model_name='interface',
            name='macaddr',
            field=models.CharField(validators=[django.core.validators.RegexValidator(code='invalid', message='Enter a valid MAC address', regex=re.compile('^([0-9A-F]{2}[:]){5}([0-9A-F]{2})$', 34))], max_length=17),
        ),
        migrations.AlterField(
            model_name='ip4address',
            name='address',
            field=models.GenericIPAddressField(protocol='IPv4'),
        ),
        migrations.AlterField(
            model_name='ip4subnet',
            name='dhcp_dynamic_end',
            field=models.GenericIPAddressField(protocol='IPv4', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='ip4subnet',
            name='dhcp_dynamic_start',
            field=models.GenericIPAddressField(protocol='IPv4', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='ip4subnet',
            name='domain_admin',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='ip4subnet',
            name='netmask',
            field=models.GenericIPAddressField(protocol='IPv4'),
        ),
        migrations.AlterField(
            model_name='ip4subnet',
            name='network',
            field=models.GenericIPAddressField(protocol='IPv4'),
        ),
        migrations.AlterField(
            model_name='ip6subnet',
            name='domain_admin',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='operatingsystem',
            name='arch',
            field=models.CharField(max_length=255, choices=[('mips', 'MIPS'), ('arm', 'ARM'), ('broadcom', 'Broadcom'), ('rc32300', 'RC32300'), ('powerpc', 'PowerPC'), ('powerpc403ga', 'PowerPC403GA'), ('unknown', 'Unknown'), ('x86_64', 'x86-64'), ('i386', 'x86')], null=True, blank=True),
        ),
    ]
