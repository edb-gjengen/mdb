from django.core.management.base import BaseCommand, CommandError
from django.core.mail import mail_admins
import sys
from optparse import make_option
from commands import getstatusoutput
from mdb.models import DhcpConfig


class Command(BaseCommand):
    args = '<poll_id poll_id ...>'
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
    )

    def handle(self, *args, **options):
        output = options['output'] if options['output'] else sys.stdout
        force = options['force']

        #dhcpd_init = "/etc/init.d/dhcp3-server %s"
        dhcpd_init = "echo %s"

        #dhcpd_config = "/etc/dhcp3/dhcpd.conf"

        config = DhcpConfig.objects.filter(name="default").get()

        if config.serial == config.active_serial and not force:
            sys.exit(0)

        dhcpd_file = open(output, 'w')
        dhcpd_file.write(config.dhcpd_configuration())
        dhcpd_file.close()

        config.active_serial = config.serial
        config.save()

        status, output = getstatusoutput(dhcpd_init % "restart")
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
