import os

from django.core.mail import mail_admins
from django.core.management.base import BaseCommand

from mdb.services.zone_sync import ZoneSyncService


class Command(BaseCommand):
    args = "[--force] [--debug]"
    help = "Generates the bind configuration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--debug",
            action="store_true",
            dest="debug",
            default=False,
            help="Debug mode. Writes to /tmp and does not reload.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            default=False,
            help="Write zone files even if serial is unchanged.",
        )
        parser.add_argument(
            "--zone",
            dest="zone",
            default=None,
            metavar="ZONE",
            help="Sync a single zone by name instead of all zones.",
        )

    def handle(self, *args, **options):
        debug = options["debug"]
        force = options["force"]
        zone_name = options["zone"]

        service = ZoneSyncService(debug=debug, force=force)

        service.validate_binaries_exist()

        os.path.isdir(service.checkzone_dir) or os.mkdir(service.checkzone_dir)
        debug and (os.path.isdir(service.debug_dir) or os.mkdir(service.debug_dir))

        if zone_name:
            zone = service.find_zone(zone_name)
            if zone is None:
                self.stderr.write("error: zone '%s' not found\n" % zone_name)
                raise SystemExit(1)
            service.sync_zone(zone)
        else:
            service.sync_all_zones()

        if service.changes and not debug:
            errors = "\n\n\n".join(
                [v["errors"] for v in service.changes.values() if v["errors"]]
            )
            diffs = "\n\n\n".join(
                [v["diff"] for v in service.changes.values() if v["diff"]]
            )
            zones = ", ".join(service.changes.keys())
            self.reload_and_notify(service, errors, diffs, zones)

    def reload_and_notify(self, service, errors, diffs, zones):
        self.stdout.write("reloading zones... ")
        success, failed_command, output = service.run_reload_commands()

        if not success:
            self.stdout.write("fail\n")
            message = (
                "Failed to reload zones, please inspect...\n\n"
                + "%s@%s$ %s" % (os.getlogin(), os.uname()[1], failed_command)
                + "\n%s\n\n\n%s\n\n\n%s" % (output, errors, diffs)
            )
            mail_admins(
                subject="FAIL: bind (%s changed: %s)" % (len(service.changes), zones),
                message=message,
                html_message="<pre>%s</pre>" % message,
            )
            raise SystemExit(1)

        self.stdout.write("ok\n")
        message = "Successfully updated bind zone files\n\n%s\n\n%s" % (errors, diffs)
        mail_admins(
            subject="Success: bind (%s changed: %s)" % (len(service.changes), zones),
            message=message,
            html_message="<pre>%s</pre>" % message,
        )
