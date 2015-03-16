from __future__ import with_statement

import os
import sys
from itertools import chain
from difflib import context_diff
from django.core.management.base import BaseCommand
from django.core.mail import mail_admins
from optparse import make_option
from commands import getstatusoutput
from mdb.models import *


class Command(BaseCommand):
    args = '[--force] [--debug]'
    help = 'Generates the bind configuration'

    option_list = BaseCommand.option_list + (
        make_option('--debug',
                    action='store_true',
                    dest='debug',
                    default=False,
                    help='Debug mode. Writes to /tmp and does not reload.'),
        make_option('--force',
                    action='store_true',
                    dest='force',
                    default=False,
                    help='Write zone files even if serial is unchanged.'),
    )

    bind_bin = "/etc/init.d/bind9"
    reload_command = "%s reload" % bind_bin
    checkzone_bin = "/usr/sbin/named-checkzone"
    checkzone_dir = "/tmp/mdb-checkzone"
    debug = False
    debug_dir = '/tmp/mdb-debug'
    changes = {}

    def handle(self, *args, **options):
        self.debug = debug = options['debug']
        force = options['force']

        # do the binaries exist?
        for f in (self.checkzone_bin, self.bind_bin):
            if not os.path.isfile(f):
                print "ERROR: no such file %s, exiting..." % f
                if not debug:
                    sys.exit(1)

        # create directories if needed
        os.path.isdir(self.checkzone_dir) or os.mkdir(self.checkzone_dir)
        debug and (os.path.isdir(self.debug_dir) or os.mkdir(self.debug_dir))

        # update zones with new serials
        for zone in chain(Domain.objects.all(),
                          Ip4Subnet.objects.all(),
                          Ip6Subnet.objects.all()):
            if zone.domain_serial == zone.domain_active_serial or force:
                continue
            self.update_zone(zone)

        # join errors and diffs
        errors = "\n\n\n".join(
            [v['errors'] for k, v in self.changes.items() if v['errors']])
        diffs = "\n\n\n".join(
            [v['diff'] for k, v in self.changes.items() if v['diff']])

        # reload and send email with changes
        if self.changes and not debug:
            sys.stdout.write("reloading bind... ")
            status, output = getstatusoutput(self.reload_command)
            if status != 0:
                sys.stdout.write("fail\n")
                mail_admins(
                    "FAIL: bind (%s changed zones)" % len(self.changes),
                    "Failed to reload bind, please inspect...\n\n" +
                    "%s@%s# %s" % (
                        os.getlogin(), os.uname()[1], self.reload_command) +
                    "\n%s\n\n\n%s\n\n\n%s" % (output, errors, diffs))
                sys.exit(1)
            else:
                sys.stdout.write("ok\n")
                mail_admins(
                    "Success: bind (%s changed zones)" % len(self.changes),
                    "Successfully updated bind zone files\n\n" +
                    "%s\n\n%s" % (errors, diffs))
                sys.exit(0)

    def update_zone(self, zone):
        zonetype = getattr(zone._meta, 'verbose_name', None) \
            or zone._meta.model_name

        self.changes[zone.domain_name] = {
            'old_serial': zone.domain_active_serial,
            'new_serial': zone.domain_serial,
            'success': False,
            'errors': None,
            'diff': None,
        }

        print "updating %s %s [%d -> %d]" % (
            zonetype,
            zone.domain_name,
            zone.domain_active_serial,
            zone.domain_serial)

        # generate zone file contents
        new = zone.zone_file_contents()

        # read current file contents
        try:
            with open(zone.domain_filename, 'r') as f:
                old = f.read()
        except IOError:
            old = ''

        # calculate diff
        diff = "\n".join(context_diff(
            a=old.splitlines(),
            b=new.splitlines(),
            fromfile=str(zone.domain_active_serial) + '-' + zone.domain_name,
            tofile=str(zone.domain_serial) + '-' + zone.domain_name,
            lineterm=''))
        self.changes[zone.domain_name]['diff'] = diff

        # validate with zonecheck
        sys.stdout.write("\t- validating... ")
        status, output = self.check_zone(zone, new)
        if status != 0:
            sys.stdout.write("fail\n")
            self.changes[zone.domain_name]['errors'] = output
            return False
        sys.stdout.write("ok\n")

        # write to zone file
        sys.stdout.write("\t- writing zone file... ")

        if not self.debug:
            zonefile = zone.domain_filename
        else:
            zonefile = self.debug_dir + zone.domain_filename
            path = "/".join(zonefile.split('/')[:-1])
            os.path.isdir(path) or os.makedirs(path)

        with open(zonefile, 'w') as f:
            f.write(new)

        # update serial
        if not self.debug:
            zone.domain_active_serial = zone.domain_serial
            zone.save()

        sys.stdout.write("ok\n")
        self.changes[zone.domain_name]['success'] = True
        return True

    def check_zone(self, zone, contents):
        zonefile = self.checkzone_dir + '/' + zone.domain_name
        with open(zonefile, 'w') as f:
            f.write(contents)

        return getstatusoutput("%s %s %s" % (
            self.checkzone_bin, zone.domain_name, zonefile))
