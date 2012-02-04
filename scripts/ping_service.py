#!/usr/bin/env python
# coding: utf-8

import os,sys,datetime

try:
	host_type = sys.argv[1]
except:
	print "USAGE: %s <host type>" % sys.argv[0]
	sys.exit(1)

from django.core.management import setup_environ
from django.core.mail import mail_admins
from dns_mdb import settings

setup_environ(settings)

from mdb.models import *

debugging = False



def do_ping(ipaddr):
	if os.system("ping -c 1 -W 1 %s > /dev/null 2>&1" % ipaddr) == 0:
		return 1
	else:
		return None

hosts = Host.objects.filter(host_type__host_type = host_type)


for host in hosts:
	interfaces = host.interface_set.all()
	
	for interface in interfaces:
		if do_ping(interface.ip4address.address):
			interface.ip4address.last_contact = datetime.datetime.now()
			interface.ip4address.save()
			if debugging:
				print "%s (%s) : success" % (host, interface.ip4address.address)
		else:
			if debugging:
				print "%s (%s) : fail   " % (host, interface.ip4address.address)
			

	


