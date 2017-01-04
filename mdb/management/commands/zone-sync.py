from __future__ import with_statement

import os
import sys
from itertools import chain
from difflib import context_diff
from django.core.management.base import BaseCommand
from django.core.mail import mail_admins
try:
    from subprocess import getstatusoutput
except ImportError:
    from commands import getstatusoutput

from mdb.models import Domain, Ip4Subnet, Ip6Subnet


class Command(BaseCommand):
    args = '[--force] [--debug]'
    help = 'Generates the bind configuration'

    rndc_bin = "/usr/sbin/rndc"
    reload_command = "%s reload" % rndc_bin
    freeze_command = "%s freeze" % rndc_bin
    thaw_command = "%s thaw" % rndc_bin
    commands_in_order = [freeze_command, reload_command, thaw_command]
    checkzone_bin = "/usr/sbin/named-checkzone"
    checkzone_dir = "/tmp/mdb-checkzone"
    debug = False
    force = False
    debug_dir = '/tmp/mdb-debug'
    changes = {}

    def add_arguments(self, parser):
        parser.add_argument('--debug',
                            action='store_true',
                            dest='debug',
                            default=False,
                            help='Debug mode. Writes to /tmp and does not reload.')
        parser.add_argument('--force',
                            action='store_true',
                            dest='force',
                            default=False,
                            help='Write zone files even if serial is unchanged.')

    def handle(self, *args, **options):
        self.debug = options['debug']
        self.force = options['force']

        # do the binaries exist?
        self.validate_binaries_exist()

        # create directories if needed
        os.path.isdir(self.checkzone_dir) or os.mkdir(self.checkzone_dir)
        self.debug and (os.path.isdir(self.debug_dir) or os.mkdir(self.debug_dir))

        # update zones with new serials
        self.update_zone_serials()

        # join errors, diffs and zone names
        errors = "\n\n\n".join(
            [v['errors'] for k, v in self.changes.items() if v['errors']])
        diffs = "\n\n\n".join(
            [v['diff'] for k, v in self.changes.items() if v['diff']])
        zones = ", ".join(self.changes.keys())

        # reload and send email with changes
        if self.changes and not self.debug:
            sys.stdout.write("reloading zones... ")
            for command in self.commands_in_order:
                status, output = getstatusoutput(command)
                if status != 0:
                    sys.stdout.write("fail\n")
                    message = (
                        "Failed to reload zones, please inspect...\n\n" +
                        "%s@%s$ %s" % (
                            os.getlogin(), os.uname()[1], command) +
                        "\n%s\n\n\n%s\n\n\n%s" % (output, errors, diffs))
                    mail_admins(
                        subject="FAIL: bind (%s changed: %s)" % (len(self.changes), zones),
                        message=message,
                        html_message='<pre>%s</pre>' % message)
                    sys.exit(1)

            sys.stdout.write("ok\n")
            message = (
                "Successfully updated bind zone files\n\n" +
                "%s\n\n%s" % (errors, diffs))
            mail_admins(
                subject="Success: bind (%s changed: %s)" % (len(self.changes), zones),
                message=message,
                html_message='<pre>%s</pre>' % message)
            sys.exit(0)

    def update_zone_serials(self):
        for zone in chain(Domain.objects.all(),
                          Ip4Subnet.objects.all(),
                          Ip6Subnet.objects.all()):
            if zone.domain_serial == zone.domain_active_serial and not self.force:
                continue

            if self.update_zone(zone):
                self.changes[zone.domain_name]['success'] = True

    def validate_binaries_exist(self):
        for f in (self.checkzone_bin, self.rndc_bin):
            if not os.path.isfile(f) and not self.debug:
                print("ERROR: no such file %s, exiting..." % f)
                if not self.debug:
                    sys.exit(1)

    def update_zone(self, zone):
        zonetype = getattr(zone._meta, 'verbose_name', None) or zone._meta.model_name

        self.changes[zone.domain_name] = {
            'old_serial': zone.domain_active_serial,
            'new_serial': zone.domain_serial,
            'success': False,
            'errors': None,
            'diff': None,
        }

        print("updating %s %s [%d -> %d]" % (
            zonetype,
            zone.domain_name,
            zone.domain_active_serial,
            zone.domain_serial))

        # generate zone file contents
        new = zone.zone_file_contents()

        # read current file contents
        try:
            with open(zone.domain_filename, 'r') as f:
                old = f.read()
        except IOError:
            old = ''

        self.changes[zone.domain_name]['diff'] = self.calculate_diff(new, old, zone)

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

    def calculate_diff(self, new, old, zone):
        return "\n".join(context_diff(
            a=old.splitlines(),
            b=new.splitlines(),
            fromfile=str(zone.domain_active_serial) + '-' + zone.domain_name,
            tofile=str(zone.domain_serial) + '-' + zone.domain_name,
            lineterm=''))

    def check_zone(self, zone, contents):
        zonefile = self.checkzone_dir + '/' + zone.domain_name
        with open(zonefile, 'w') as f:
            f.write(contents)

        return getstatusoutput("%s %s %s" % (self.checkzone_bin, zone.domain_name, zonefile))
