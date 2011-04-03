#!/usr/bin/env python
# coding: utf-8

import datetime, os, commands, sys, shutil
from django.core.management import setup_environ
#from dns_mdb import settings
import settings

setup_environ(settings)

from mdb.models import *


to_be_updated = []
zones = {}
zone_file_temp_dir = "temp"
zone_file_dir = "/var/lib/bind"
zone_command = "/usr/sbin/named-checkzone %s %s"

if not os.path.isdir(zone_file_temp_dir):
	os.mkdir(zone_file_temp_dir)


class Log():
	filename = None
	started = False

	def startlog(self):
		if self.started:
			return
		logfile = open(self.filename, "a")
		logfile.write("\nStarting log %s\n" % str(datetime.datetime.now()))
		logfile.close()
		self.started = True

	def setFilename(self, filename):
		self.filename = filename
	
	def debug(self, string):
		self.startlog()
		logfile = open(self.filename, "a")
		logfile.write("%s\n" % string)
		logfile.close()
		print string

log = Log()
log.setFilename("dns_sync.log")

def valid_zone(zone, filename):
	status, output = commands.getstatusoutput(zone_command % (zone, filename))
	if status != 0:
		print "Could not validate zone:\n%s" % output
		return False
	else:
		return True


# this will produce the zone files for the domains
domains = Domain.objects.all()
for domain in domains:
	current_serial = 0
	if os.path.exists("%s/%s" % (zone_file_dir, domain.domain_filename)):
		zonefile = open("%s/%s" % (zone_file_dir,domain.domain_filename), "r")
		firstline = zonefile.readline()
		current_serial = int( firstline.split(":")[1])
		
		zonefile.close()
	
	if current_serial < domain.domain_serial:
		log.debug("Updating zone %s from %d -> %d" %
			(domain.domain_name, current_serial, domain.domain_serial))
		zone_contents = domain.zone_file_contents()
		zonefile = open("%s/%s" % (zone_file_temp_dir, domain.domain_filename),"w")
		zonefile.write(zone_contents)
		zonefile.close()
		if valid_zone(domain.domain_name, "%s/%s" %
				(zone_file_temp_dir, domain.domain_filename)):
			to_be_updated.append( [ domain.domain_name, "%s/%s" %
				(zone_file_temp_dir, domain.domain_filename) ] )

# this will produce the zone files for the reverse lookup subnets
subnets = Ip4Subnet.objects.all()
for domain in subnets:
	current_serial = 0
	if os.path.exists("%s/%s" % (zone_file_dir, domain.domain_filename)):
		zonefile = open("%s/%s" % (zone_file_dir,domain.domain_filename), "r")
		firstline = zonefile.readline()
		current_serial = int( firstline.split(":")[1])
		
		zonefile.close()
	
	if current_serial < domain.domain_serial:
		log.debug("Updating zone %s from %d -> %d" %
			(domain.domain_name, current_serial, domain.domain_serial))
		zone_contents = domain.zone_file_contents()
		zonefile = open("%s/%s" % (zone_file_temp_dir, domain.domain_filename),"w")
		zonefile.write(zone_contents)
		zonefile.close()
		if valid_zone(domain.domain_name, "%s/%s" %
				(zone_file_temp_dir, domain.domain_filename)):
			to_be_updated.append( [ domain.domain_name, "%s/%s" %
				(zone_file_temp_dir, domain.domain_filename) ] )

if len(to_be_updated) == 0:
	# nothing to do
	sys.exit(0)

for upd in to_be_updated:
	shutil.copy(upd[1], zone_file_dir)

status, output = commands.getstatusoutput("/etc/init.d/bind9 reload")

if status != 0:
	print output
	sys.exit(1)

sys.exit(0)

