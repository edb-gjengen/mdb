# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mdb', '0009_auto_20151004_1652'),
    ]

    operations = [
        migrations.CreateModel(
            name='DomainAAAARecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('target', models.GenericIPAddressField(protocol='IPv6')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('domain', models.ForeignKey(to='mdb.Domain', on_delete=models.CASCADE)),
            ],
        ),
        migrations.AlterField(
            model_name='domainarecord',
            name='target',
            field=models.GenericIPAddressField(protocol='IPv4'),
        ),
    ]
