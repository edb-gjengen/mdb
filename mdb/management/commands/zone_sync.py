import getpass
import os
import signal

from django.core.management.base import BaseCommand

from mdb.services import discord
from mdb.services.zone_sync import ZoneSyncService

# What stops a sync run by hand: a dropped ssh session, a kill, Ctrl-C.
STOPPING_SIGNALS = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)


class Interrupted(Exception):
    def __init__(self, signum):
        self.signum = signum
        super().__init__(signal.Signals(signum).name)


def raise_interrupted(signum, frame):
    raise Interrupted(signum)


def set_handlers(handler):
    for signum in STOPPING_SIGNALS:
        signal.signal(signum, handler)


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

        if not debug:
            self.thaw_after_killed_sync(service)

        if zone_name:
            zone = service.find_zone(zone_name)
            if zone is None:
                self.stderr.write(f"error: zone '{zone_name}' not found\n")
                raise SystemExit(1)
            zones = [zone]
        else:
            zones = service.pending_zones()

        if not zones:
            return

        if debug:
            for zone in zones:
                service.sync_zone(zone)
            return

        previous = {signum: signal.getsignal(signum) for signum in STOPPING_SIGNALS}
        try:
            # From the freeze to the thaw, a signal must not stop the sync in between:
            # ignored while rndc runs, it stops the writes for a reload and thaw.
            set_handlers(signal.SIG_IGN)
            self.freeze(service, zones)
            set_handlers(raise_interrupted)
            try:
                for zone in zones:
                    service.sync_zone(zone)
            except BaseException as e:
                set_handlers(signal.SIG_IGN)
                self.reload_after_interruption(service, zones, e)
                if isinstance(e, Interrupted):
                    raise SystemExit(128 + e.signum) from e
                raise
            set_handlers(signal.SIG_IGN)
            self.reload_and_notify(service, service.changes)
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)

    def thaw_after_killed_sync(self, service):
        since = service.frozen_since()
        if since is None:
            return

        self.stdout.write("a previous sync left the zones frozen, thawing... ")
        summary = (
            f"A zone sync killed after {since:%Y-%m-%d %H:%M} left every zone frozen"
        )
        success, failed_command, output = service.reload()
        if not success:
            self.stdout.write("fail\n")
            self.notify_failure(
                f"{summary}, and thawing them failed", failed_command, output, []
            )
        self.stdout.write("ok\n")
        discord.notify(
            subject="⚠️ Zones thawed after a killed zone sync",
            message=f"{summary}, refusing dynamic updates until now. "
            "They are reloaded and thawed.",
        )

    def reload_after_interruption(self, service, zones, error):
        reason = str(error) if isinstance(error, Interrupted) else repr(error)
        written = [z for z, c in service.changes.items() if c["success"]]
        not_written = [z.domain_name for z in zones if z.domain_name not in written]

        self.stdout.write(f"stopped by {reason}, reloading zones... ")
        success, failed_command, output = service.reload()
        if not success:
            self.stdout.write("fail\n")
            self.notify_failure(
                f"Zone sync stopped by {reason}, and reloading the zones failed; "
                "they may still be frozen",
                failed_command,
                output,
                not_written,
            )
        self.stdout.write("ok\n")
        message = f"Zone sync stopped by {reason}. The zones are reloaded and thawed."
        if written:
            message += "\n\nWritten:\n" + "\n".join("- " + z for z in written)
        if not_written:
            message += "\n\nNot written, run mdb-sync again:\n" + "\n".join(
                "- " + z for z in not_written
            )
        discord.notify(subject="⚠️ Zone sync interrupted, zones thawed", message=message)

    def freeze(self, service, zones):
        self.stdout.write("freezing zones... ")
        success, failed_command, output = service.freeze()
        if not success:
            self.stdout.write("fail\n")
            # A failed freeze may have frozen some zones before stopping.
            service.thaw()
            self.notify_failure(
                "Failed to freeze zones, nothing was written",
                failed_command,
                output,
                [z.domain_name for z in zones],
            )
        self.stdout.write("ok\n")

    def reload_and_notify(self, service, changes):
        self.stdout.write("reloading zones... ")
        success, failed_command, output = service.reload()

        if not success:
            self.stdout.write("fail\n")
            errors = "\n\n\n".join(
                [v["errors"] for v in changes.values() if v["errors"]]
            )
            diffs = "\n\n\n".join([v["diff"] for v in changes.values() if v["diff"]])
            self.notify_failure(
                "Failed to reload zones",
                failed_command,
                output,
                list(changes.keys()),
                errors,
                diffs,
            )

        self.stdout.write("ok\n")
        for zone, info in changes.items():
            message = f"Successfully updated bind zone file for `{zone}`"
            if info["errors"]:
                message += "\n\n" + info["errors"]
            discord.notify(
                subject="✅ Success: bind",
                message=message,
                preformatted=info["diff"] or None,
            )

    def notify_failure(
        self, summary, failed_command, output, zones, errors="", diffs=""
    ):
        zone_list = "\n".join("- " + z for z in zones)
        message = f"{summary}, please inspect...\n\n{getpass.getuser()}@{os.uname()[1]}$ {failed_command}\n{output}\n{zone_list}"
        if errors:
            message += "\n\n" + errors
        discord.notify(
            subject="⚠️ FAIL: bind",
            message=message,
            preformatted=diffs or None,
        )
        raise SystemExit(1)
