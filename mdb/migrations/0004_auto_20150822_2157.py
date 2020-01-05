# -*- coding: utf-8 -*-
from django.db import models, migrations
from django.db.migrations import RunPython


def flatten_architecture(apps, schema_editor):
    OperatingSystem = apps.get_model("mdb", "OperatingSystem")
    for os in OperatingSystem.objects.all():
        os.arch = os.architecture.architecture
        os.save()


class Migration(migrations.Migration):
    dependencies = [
        ('mdb', '0003_auto_20150822_2156'),
    ]

    operations = [
        RunPython(flatten_architecture),
    ]
