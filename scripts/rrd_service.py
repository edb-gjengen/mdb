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

args = parser.parse_args()

from django.core.management import setup_environ
from django.core.mail import mail_admins
from dns_mdb import settings
setup_environ(settings)
from mdb.models import *

PING_CMD='ping -W 1 -c %d -n -q %s | grep rtt | cut -d " " -f4'

queue = Queue.Queue()


RRD_CREATE = "%s " \
        "DS:ttl:GAUGE:600:U:U "\
        "RRA:AVERAGE:0.5:1:576 "\
        "RRA:AVERAGE:0.5:6:336 "\
        "RRA:AVERAGE:0.5:72:124 "\
        "RRA:AVERAGE:0.5:288:365"

RRD_UPDATE = "%s --template rtt N:%s"

RRD_DIR = args.rrd_path
RRDTOOL = "/usr/bin/rrdtool"

class RrdService():
    def log(self, host, interface, avg_ping):
        rrd = self.get_rrd(host, interface)
        self.update_rrd(rrd, avg_ping)

    def get_rrd(self, host, interface):
        return "%s/%s_%s.rrd" % ( RRD_DIR, host.id,\
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
    def rrd_exec(self, function, rrd_cmd):
        cmd = "%s %s %s" % (RRDTOOL, function, rrd_cmd)
        if args.debug:
            print "RRD_EXEC (%s)" % cmd
        if os.system(cmd) != 0:
            return False
        else:
            return True

class PingThread(threading.Thread):
    """ Threaded ping """
    def __init__(self, host_queue, rrd_service):
        threading.Thread.__init__(self)
        self.queue = queue
        self.rrd_service = rrd_service

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
        if args.debug:
            print "%s (%s/%s) : %s" % (host, interface.name, \
                interface.ip4address.address, res)
        self.rrd_service.log(host,interface, res[1])

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

rrd_service = RrdService()

# start num_threads threads for pinging
for i in xrange(args.num_threads):
    t = PingThread(queue, rrd_service)
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
