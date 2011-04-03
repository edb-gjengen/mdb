#!/usr/bin/env python
# coding: utf-8

import datetime, os, commands, sys, shutil
from django.core.management import setup_environ
import settings

setup_environ(settings)

from mdb.models import *

to_be_updated = []
dhcp_filename = "dhcpd.conf"
dhcp_file_temp_dir = "dhcp"
#dhcp_file_dir = "/etc/dhcp"
dhcp_file_dir = "dhcp2"

dhcp_orig_file = "%s/%s" % (dhcp_file_dir, dhcp_filename)
dhcp_temp_file = "%s/%s" % (dhcp_file_temp_dir, dhcp_filename)

dhcp_orig_serial = 0

if not os.path.isdir(dhcp_file_temp_dir):
	os.mkdir(dhcp_file_temp_dir)

if not os.path.isdir(dhcp_file_dir):
	os.mkdir(dhcp_file_dir)

# read the current dhcp configs first line to get the serial
if os.path.exists(dhcp_orig_file):
	dhcp_orig_fd = open(dhcp_orig_file, "r")
	dhcp_orig_serial = int(dhcp_orig_fd.readline().split(":")[1])
	dhcp_orig_fd.close()


# fetch configuration option #1
# we don't support more then one at this time.
config = DhcpConfig.objects.all()[0]

if config.serial <= dhcp_orig_serial:
	print "no update nesecarry"
#	sys.exit(0)

# open a temporary file to build the new configuration
dhcp_temp_fd = open(dhcp_temp_file, "w")

# write the new serial to the file
dhcp_temp_fd.write("; serial:%s\n" % config.serial)

# write if the dhcp server is authoritative
if config.authoritative:
	dhcp_temp_fd.write("authoritative;\n")

# write default lease time
dhcp_temp_fd.write("default-lease-time %d;\n" % config.default_lease_time)

# write max lease time
dhcp_temp_fd.write("max-lease-time %d;\n" % config.max_lease_time)

# write log facility
dhcp_temp_fd.write("log-facility %s;\n" % config.log_facility)

# write update style
dhcp_temp_fd.write("ddns-update-style %s;\n" % config.ddns_update_style)



for subnet in config.ip4subnet_set.all():
	dhcp_temp_fd.write("\n# %s\n" % subnet.name)
	dhcp_temp_fd.write("subnet %s netmask %s {\n" % (subnet.network, subnet.netmask))

	for option in subnet.dhcpoption_set.all():
		dhcp_temp_fd.write("\toption %s %s;\n" % (option.key, option.value))

	for option in subnet.dhcpcustomfield_set.all():
		dhcp_temp_fd.write("\t%s;\n" % option.value)

	if subnet.dhcp_dynamic:
		dhcp_temp_fd.write("\trange %s %s;\n"
			% (subnet.dhcp_dynamic_start, subnet.dhcp_dynamic_end))

	dhcp_temp_fd.write("}\n")


for subnet in config.ip4subnet_set.all():
	if not subnet.dhcp_dynamic: continue

	for ip4address in subnet.ip4address_set.all():
		if ip4address.interface_set.count() == 0: continue
		interface = ip4address.interface_set.get()
		if not interface.dhcp_client: continue
		
		dhcp_temp_fd.write("\nhost %s {\n" % interface.host.hostname)
		dhcp_temp_fd.write("\thardware ethernet %s;\n" % interface.macaddr)
		dhcp_temp_fd.write("\tfixed-address %s.%s;\n"
			% (interface.host.hostname, interface.domain.domain_name))
		dhcp_temp_fd.write("}\n")
		
#		print "found interface %s\n" % interface

dhcp_temp_fd.close()


shutil.copy(dhcp_temp_file, dhcp_orig_file)

sys.exit(0)
