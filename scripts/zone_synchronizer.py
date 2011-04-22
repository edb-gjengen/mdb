#!/usr/bin/env python
# coding: utf-8

import os,sys
from commands import getstatusoutput

from django.core.management import setup_environ
from django.core.mail import mail_admins
from dns_mdb import settings

setup_environ(settings)

from mdb.models import *

bind_init = "/etc/init.d/bind9 %s"

error_log_file = "/tmp/zonecheck/zonecheck-fail-%s-%s"

zone_check_command = "/usr/sbin/named-checkzone %s %s"
zone_check_temp_dir = "/tmp/zonecheck"
zone_check_temp_file = "%s/%s" % ( zone_check_temp_dir, "zone" )

if not os.path.isfile( (zone_check_command % ("","")).strip()):
	print "ERROR: cannot find zone checking tool, exiting..."
	sys.exit(1)

if not os.path.isfile( (bind_init % ("")).strip()):
	print "ERROR: cannot find bind init script, exiting..."
	sys.exit(1)

if not os.path.isdir(zone_check_temp_dir):
	os.mkdir(zone_check_temp_dir)

def check_zone(zone, filename):
	retval = {}
	
	status, output = getstatusoutput(zone_check_command % (zone, filename))
	retval['value'] = status
	retval['output'] = output

	return retval

reload_bind = False

for domain in Domain.objects.all():
	if domain.domain_serial == domain.domain_active_serial:
		continue
	
	print "updating domain %s [%d -> %d]" % \
		(domain.domain_name, domain.domain_active_serial, \
		domain.domain_serial)

	sys.stdout.write("\t- validating...")
	zonecheck = open(zone_check_temp_file, "w")
	zonecheck.write(domain.zone_file_contents())
	zonecheck.close()

	result = check_zone(domain.domain_name, zone_check_temp_file)
	if result['value'] != 0:
		sys.stdout.write("fail\n")
		log = open(error_log_file % (domain.domain_name, \
			domain.domain_serial))
		log.write(output)
		log.close()
		continue
	
	sys.stdout.write("ok\n")

	sys.stdout.write("\t- writing zone file...")
	zonefile = open(domain.domain_filename, "w")
	zonefile.write(domain.zone_file_contents())
	zonefile.close()
	sys.stdout.write("ok\n")

	reload_bind = True

	domain.domain_active_serial = domain.domain_serial
	domain.save()
	
for subnet in Ip4Subnet.objects.all():
	if subnet.domain_serial == subnet.domain_active_serial:
		continue
	print "updating subnet %s [%d -> %d]" % \
		(subnet.domain_name, subnet.domain_active_serial, \
		subnet.domain_serial)
	
	sys.stdout.write("\t- validating...")
	zonecheck = open(zone_check_temp_file, "w")
	zonecheck.write(subnet.zone_file_contents())
	zonecheck.close()
	sys.stdout.write("ok\n")

	result = check_zone(subnet.domain_name, zone_check_temp_file)
	if result['value'] != 0:
		sys.stdout.write("fail\n")
		log = open(error_log_file % (subnet.domain_name, \
			subnet.domain_serial))
		log.write(output)
		log.close()		
		continue

	sys.stdout.write("\t- writing zone file...")
	zonefile = open(subnet.domain_filename, "w")
	zonefile.write(subnet.zone_file_contents())
	zonefile.close()
	sys.stdout.write("ok\n")

	reload_bind = True

	subnet.domain_active_serial = subnet.domain_serial
	subnet.save()

if reload_bind:
	sys.stdout.write("restarting bind...")
	status, output = getstatusoutput(bind_init % "reload")
	if status != 0:
		sys.stdout.write("fail\n")
		mail_admins("Failed to reload bind", "Failed to reload bind, plase inspect...\n\n" + \
			output)
	else:
		sys.stdout.write("ok\n")
