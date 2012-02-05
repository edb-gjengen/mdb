#!/usr/bin/env python
# coding: utf-8

import os,sys,datetime,argparse,threading,time,Queue
from commands import getstatusoutput

parser = argparse.ArgumentParser(description = 'Ping hosts from mdb')

parser.add_argument('-t', '--type', default='all',\
	help="Which type of host to operate on")
parser.add_argument('-d', '--debug', action='store_true',\
	help="Turn on debugging")
parser.add_argument('--show-types', dest='show_types', action='store_true',\
	help='Show available host types')
parser.add_argument('--num-threads', dest='num_threads', type=int, default=1,\
	help='Number of threads used for pinging hosts')
parser.add_argument('--num-pings', dest='num_pings', type=int, default=5,\
	help='Number of ping requests to each host. More requests gives a more accurate average calculation.')

args = parser.parse_args()

#project_path = '/opt/django/dns_mdb/'
#if project_path not in sys.path:
#    sys.path.append(project_path)

from django.core.management import setup_environ
from django.core.mail import mail_admins
from dns_mdb import settings
setup_environ(settings)
from mdb.models import *

PING_CMD='ping -W 1 -c %d -n -q %s | grep rtt | cut -d " " -f4'

queue = Queue.Queue()


RRD_CREATE = "%s/%s_%s.rrd " \
		"DS:ttl:GAUGE:600:U:U "\
		"RRA:AVERAGE:0.5:1:576 "\
		"RRA:AVERAGE:0.5:6:336 "\
		"RRA:AVERAGE:0.5:72:124 "\
		"RRA:AVERAGE:0.5:288:365"

RRD_DIR = "../rrd"

class RrdService():
	def __init__(self, host, interface):
		self.host = host
		self.interface = interface

	def log(self, avg_ping):
		self.update_rrd(avg_ping)

	def update_rrd(self, avg_ping):
		self.create_rrd()

	def create_rrd(self):
		rrd_file = RRD_CREATE % (RRD_DIR, host.hostname, interface.name)
		if args.debug:
			print "RRD_FILE : %s " % rrd_file
#		if not os.system(RRD_CREATE % (RRD_DIR, host.hostname, interface.name)):
#			if args.debug:
#				print "Could not create RRD database."
#			return False
		return True

class PingThread(threading.Thread):
	""" Threaded ping """
	def __init__(self, host_queue):
		threading.Thread.__init__(self)
		self.queue = queue

	def run(self):
		while True:
			host = self.queue.get()
			self.do_ping_host(host)
			self.queue.task_done()

	def do_ping_host(self, host):
		interfaces = host.interface_set.all()
		for interface in interfaces:
			self.do_ping_interface(interface, host)

	def do_ping_interface(self, interface, host):
		res = self.do_ping_ipaddr(interface.ip4address.address)
		if res == None:
			if args.debug:
				print "%s (%s/%s) : fail   " % (host, \
					interface.name, interface.ip4address.address)
			return
		interface.ip4address.last_contact = datetime.datetime.now()
		interface.ip4address.ping_avg_rtt = float(res[1])
#		interface.ip4address.save()
		if args.debug:
			print "%s (%s/%s) : %s" % (host, interface.name, \
				interface.ip4address.address, res)
	


	def do_ping_ipaddr(self, ipaddr):
		status, output = getstatusoutput(PING_CMD % (args.num_pings,ipaddr))
		if status == 0 and len(output) > 0:
			return output.split("/")
		else:
			return None
	

def show_host_types():
	types = HostType.objects.all()
	for t in types:
		print "%s (%s)" % (t.host_type, t.description)

if args.show_types:
	show_host_types()
	sys.exit(0)

if args.type == "all":
	hosts = Host.objects.all()
else:
	hosts = Host.objects.filter(host_type__host_type = args.type)

# start num_threads threads for pinging
for i in xrange(args.num_threads):
	t = PingThread(queue)
	t.setDaemon(True)
	t.start()

if args.debug:
	print "Pinging %d hosts using %d threads." % (len(hosts), args.num_threads)

# Add all hosts to the queue. Ping threads
# will pick hosts from this queue.
for host in hosts:
	queue.put(host)

# Wait for all threads to finish, eg. queue is empty.
queue.join()

# Finally, we update all hosts.
for host in hosts:
	for interface in host.interface_set.all():
		print "Saving interface %s " % interface.ip4address
		interface.ip4address.save()
