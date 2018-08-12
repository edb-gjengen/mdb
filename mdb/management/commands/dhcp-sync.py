import os
import sys
from difflib import context_diff
from django.core.management.base import BaseCommand
from django.core.mail import mail_admins
from subprocess import getstatusoutput

from mdb.models import DhcpConfig


class Command(BaseCommand):
    args = '--output <path> [--force] [--restart]'
    help = 'Generates the DHCP configuration'

    def add_arguments(self, parser):
        parser.add_argument('--output',
                            action='store',
                            dest='output',
                            default=None,
                            help='Path to dhcpd.conf, defaults to stdout'),
        parser.add_argument('--force',
                            action='store_true',
                            dest='force',
                            default=False,
                            help='Write configuration even if serial is unchanged.'),
        parser.add_argument('--restart',
                            action='store_true',
                            dest='restart',
                            default=False,
                            help='Restart dhcp3-server if serial is changed'),

    def handle(self, *args, **options):
        output = options['output'] if options['output'] else sys.stdout
        force = options['force']
        restart = options['restart']
        restart_command = "/usr/sbin/service isc-dhcp-server restart"

        config = DhcpConfig.objects.filter(name="default").get()

        # do we need to do anything?
        if config.serial == config.active_serial and not force:
            print("Nothing to do, serial is the same: %s" % config.serial)
            sys.exit(0)

        # write to stdout
        if output == sys.stdout:
            print(config.dhcpd_configuration())
            print('Not writing to file, serial not updated')
            return

        # read current file contents
        try:
            with open(output, 'r') as f:
                old = f.read()
        except IOError:
            old = ''

        # write to file
        new = config.dhcpd_configuration()
        with open(output, 'w') as f:
            f.write(new)

        diff = self.calculate_diff(config, new, old)

        print(diff)

        # update serial
        old_serial = config.active_serial
        config.active_serial = config.serial
        config.save()

        # restart the dhcp server?
        if restart:
            status, output = getstatusoutput(restart_command)
            if status != 0:
                message = (
                    "Failed to restart dhcp3-server, please inspect...\n\n" +
                    "%s@%s# %s" % (os.getlogin(), os.uname()[1], restart_command) +
                    "\n%s\n\n%s" % (output, diff))
                mail_admins(
                    subject="FAIL: dhcpd %s -> %s" % (old_serial, config.active_serial),
                    message=message,
                    html_message='<pre>%s</pre>' % message)
                sys.exit(1)
            else:
                message = (
                    "Updated dhcpd configuration to serial %d\n\n" % config.active_serial +
                    "%s" % diff)
                mail_admins(
                    subject="Success: dhcpd %s -> %s" % (old_serial, config.active_serial),
                    message=message,
                    html_message='<pre>%s</pre>' % message)
                sys.exit(0)

    def calculate_diff(self, config, new, old):
        return "\n".join(context_diff(
            a=old.splitlines(),
            b=new.splitlines(),
            fromfile=str(config.active_serial),
            tofile=str(config.serial),
            lineterm=''))
