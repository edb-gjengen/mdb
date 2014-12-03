from __future__ import with_statement
from contextlib import closing

import sys
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import mail_admins
from commands import getstatusoutput
from mdb.models import DhcpConfig


class Command(BaseCommand):
    args = '--output <path> [--force] [--restart]'
    help = 'Generates the DHCP configuration'

    option_list = BaseCommand.option_list + (
        make_option('--output',
                    action='store',
                    dest='output',
                    default=None,
                    help='Path to dhcpd.conf, defaults to stdout'),
        make_option('--force',
                    action='store_true',
                    dest='force',
                    default=False,
                    help='Write to output even if serial is unchanged.'),
        make_option('--restart',
                    action='store_true',
                    dest='restart',
                    default=False,
                    help='Restart dhcp3-server if serial is changed'),
    )

    def handle(self, *args, **options):
        output = options['output'] if options['output'] else sys.stdout
        force = options['force']
        restart = options['restart']

        dhcpd_init = "/etc/init.d/dhcp3-server"

        config = DhcpConfig.objects.filter(name="default").get()

        # do we need to do anything?
        if config.serial == config.active_serial and not force:
            print "Nothing to do, serial is the same: %s" % config.serial
            sys.exit(0)

        # write config
        if output == sys.stdout:
            print config.dhcpd_configuration()
        else:
            with closing(open(output, 'w')) as f:
                f.write(config.dhcpd_configuration())

        # update serial
        config.active_serial = config.serial
        config.save()

        # restart the dhcp server?
        if restart:
            status, output = getstatusoutput("%s restart" % dhcpd_init)
            if status != 0:
                mail_admins(
                    "Failed to restart dhcp3-server",
                    "Failed to restart dhcp3-server, please inspect...\n\n" + output)
                sys.exit(1)
            else:
                mail_admins(
                    "Update dhcpd configuration success!",
                    "Updated dhcpd configuration to serial %d." % config.active_serial)
                sys.exit(0)
