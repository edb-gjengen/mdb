#!/usr/bin/env python
# coding: utf-8

from django.core.management import setup_environ
from dns_mdb import settings

setup_environ(settings)

from mdb.models import *

