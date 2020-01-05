# -*- coding: utf-8 -*-

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mdb', '0004_auto_20150822_2157'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='operatingsystem',
            name='architecture',
        ),
        migrations.DeleteModel(
            name='OsArchitecture',
        ),
    ]
