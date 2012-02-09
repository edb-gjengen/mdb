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
parser.add_argument('--rrd-path', dest='rrd_path', required=True,\
	help='Specify the path to the rrd files')
parser.add_argument('--graph-path', dest='graph_path', required=True,\
	help="Specify the output directory for the graphs")

args = parser.parse_args()

from django.core.management import setup_environ
from django.core.mail import mail_admins
from dns_mdb import settings
setup_environ(settings)
from mdb.models import *

queue = Queue.Queue()

RRD_GRAPH = 	"%s " \
		"-w 785 -h 120 -a PNG " \
		"--slope-mode " \
		"--start -86400 --end now " \
		"--font DEFAULT:7: "\
		"--title \"%s\" " \
		"--watermark \"NEUF.NO\" " \
		"--vertical-label \"latency(ms)\" " \
		"--right-axis-label \"latency(ms)\" " \
		"--lower-limit 0 " \
		"--right-axis 1:0 " \
		"--x-grid MINUTE:10:HOUR:1:MINUTE:120:0:%%R " \
		"--alt-y-grid --rigid " \
		"DEF:roundtrip=%s:rrd:AVERAGE " \
		"LINE1:roundtrip#0000FF:\"latency(ms)\" "

# RRD_GRAPH ARGS: <output_filename.png>, <title>, <rrd>

RRD_DIR = args.rrd_path
RRD_GRAPH_DIR = args.graph_path
RRDTOOL = "/usr/bin/rrdtool"

class RrdService():
	def log(self, host, interface, avg_ping):
		rrd = self.get_rrd(host, interface)
		self.update_rrd(rrd, avg_ping)

	def get_rrd(self, host, interface):
		return "%s/%s_%s.rrd" % ( RRD_DIR, host.id,\
			interface.id)

	def get_png(self, host, interface):
		return "%s/%s_%s.png" % (RRD_GRAPH_DIR, host.id,\
			interface.id)

	def update_rrd(self, rrd, avg_ping):
		self.create_rrd(rrd)
		
		self.rrd_exec("update", RRD_UPDATE % (rrd, avg_ping))

	def create_rrd(self, rrd):
		if os.path.isfile(rrd):
			return True
		if args.debug:
			print "Creating rrd: " + rrd
		if not self.rrd_exec("create", RRD_CREATE % rrd):
			if args.debug:
				print "Could not create RRD database."
			return False
		return True

	def create_title(self, host, interface):
#		return "%s (%s)" % (host.hostname, unicode(interface))
		return unicode(interface)

	def create_graph(self, host, interface):
		rrd = self.get_rrd(host, interface)
		if not os.path.isfile(rrd): return 

		self.rrd_exec("graph", RRD_GRAPH % (self.get_png(host, interface), \
			self.create_title(host, interface), rrd))

	def rrd_exec(self, function, rrd_cmd):
		cmd = "%s %s %s" % (RRDTOOL, function, rrd_cmd)
		if args.debug:
			print "RRD_EXEC (%s)" % cmd
		if os.system(cmd) != 0:
			return False
		else:
			return True

class WorkerThread(threading.Thread):
	""" Threaded ping """
	def __init__(self, host_queue, rrd_service):
		threading.Thread.__init__(self)
		self.queue = queue
		self.rrd_service = rrd_service

	def run(self):
		while True:
			host = self.queue.get()
			self.do_graph_host(host)
			self.queue.task_done()

	def do_graph_host(self, host):
		interfaces = host.interface_set.all()
		for interface in interfaces:
			self.rrd_service.create_graph(host, interface)

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

rrd_service = RrdService()

# start num_threads threads for pinging
for i in xrange(args.num_threads):
	t = WorkerThread(queue, rrd_service)
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

sys.exit(0)
