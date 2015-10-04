# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mdb', '0007_auto_20151003_1313'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ip6address',
            name='address',
            field=models.GenericIPAddressField(protocol='IPv6'),
        ),
    ]
