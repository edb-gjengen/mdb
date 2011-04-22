#!/usr/bin/env python
# coding: utf-8

import os,sys
from commands import getstatusoutput

from django.core.management import setup_environ
from django.core.mail import mail_admins
from dns_mdb import settings

setup_environ(settings)

from mdb.models import *

debugging = False

dhcpd_init = "/etc/init.d/dhcp3-server %s"

dhcpd_config = "/etc/dhcp3/dhcpd.conf"
#dhcpd_config = "dhcpd.conf"


config = DhcpConfig.objects.filter(name = "default").get()


if config.serial == config.active_serial and not debugging:
	sys.exit(0)

dhcpd_file = open(dhcpd_config , "w")
dhcpd_file.write(config.dhcpd_configuration())
dhcpd_file.close()

config.active_serial = config.serial
config.save()

status, output = getstatusoutput(dhcpd_init % "restart")
if status != 0:
	mail_admins("Failed to restart dhcp3-server", \
		"Failed to restart dhcp3-server, plase inspect...\n\n" + output)
	sys.exit(1)
else:
	mail_admins("Update dhcpd configuration success!", \
		"Updated dhcpd configuration to serial %d." % \
		config.active_serial)
	sys.exit(0)

