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
		interface.ip4address.save()
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
