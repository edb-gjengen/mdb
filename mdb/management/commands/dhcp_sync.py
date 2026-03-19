import os

from django.core.management.base import BaseCommand

from mdb.services import discord
from mdb.services.dhcp_sync import DhcpSyncService


class Command(BaseCommand):
    args = "--output <path> [--force] [--restart]"
    help = "Generates the DHCP configuration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            action="store",
            dest="output",
            default=None,
            help="Path to dhcpd.conf, defaults to stdout",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            default=False,
            help="Write configuration even if serial is unchanged.",
        )
        parser.add_argument(
            "--restart",
            action="store_true",
            dest="restart",
            default=False,
            help="Restart isc-dhcp-server if serial is changed",
        )

    def handle(self, *args, **options):
        output = options["output"]
        force = options["force"]
        restart = options["restart"]

        service = DhcpSyncService(force=force)
        config = service.get_config()

        if not service.needs_update(config):
            self.stdout.write("Nothing to do, serial is the same: %s\n" % config.serial)
            return

        if output is None:
            self.stdout.write(config.dhcpd_configuration())
            self.stdout.write("Not writing to file, serial not updated\n")
            return

        old_serial, diff = service.write_config(config, output)
        self.stdout.write(diff + "\n")

        if restart:
            self.restart_and_notify(service, config, old_serial, diff)

    def restart_and_notify(self, service, config, old_serial, diff):
        self.stdout.write("restarting isc-dhcp-server... ")
        success, output = service.restart_service()

        if not success:
            self.stdout.write("fail\n")
            message = (
                "Failed to restart isc-dhcp-server, please inspect...\n\n"
                "%s@%s$ %s\n%s"
                % (os.getlogin(), os.uname()[1], service.restart_command, output)
            )
            discord.notify(
                subject="⚠️ FAIL: dhcpd %s -> %s" % (old_serial, config.active_serial),
                message=message,
                preformatted=diff or None,
            )
            raise SystemExit(1)

        self.stdout.write("ok\n")
        message = "Updated dhcpd configuration to serial %d" % config.active_serial
        discord.notify(
            subject="✅ Success: dhcpd %s -> %s" % (old_serial, config.active_serial),
            message=message,
            preformatted=diff or None,
        )
