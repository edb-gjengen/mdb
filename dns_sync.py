#!/usr/bin/env python
# coding: utf-8

import datetime
from django.core.management import setup_environ
#from dns_mdb import settings
import settings

setup_environ(settings)

from mdb.models import *

domains = Domain.objects.all()

zones = {}

for domain in domains:
	print domain.zone_file_contents()
