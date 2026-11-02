import os
import re
import shutil
import stat
import sys
import tempfile
from datetime import datetime
from difflib import context_diff
from itertools import chain
from subprocess import getstatusoutput

from mdb.models import Domain, Ip4Subnet, Ip6Subnet


class ZoneSyncService:
    rndc_bin = shutil.which("rndc") or "/usr/sbin/rndc"
    freeze_command = f"{rndc_bin} freeze"
    reload_command = f"{rndc_bin} reload"
    thaw_command = f"{rndc_bin} thaw"
    checkzone_bin = shutil.which("named-checkzone") or "/usr/sbin/named-checkzone"
    compilezone_bin = shutil.which("named-compilezone") or "/usr/sbin/named-compilezone"
    checkzone_dir = "/tmp/mdb-checkzone"
    debug_dir = "/tmp/mdb-debug"

    def __init__(self, debug=False, force=False):
        self.debug = debug
        self.force = force
        self.changes = {}

    def validate_binaries_exist(self):
        for f in (self.checkzone_bin, self.compilezone_bin, self.rndc_bin):
            if not os.path.isfile(f) and not self.debug:
                print(f"ERROR: no such file {f}, exiting...")
                sys.exit(1)

    def run_commands(self, commands):
        """Execute commands in order, stopping at the first failure.

        Returns (success, failed_command, output). On success, failed_command
        and output are empty strings.
        """
        for command in commands:
            status, output = getstatusoutput(command)
            if status != 0:
                return False, command, output
        return True, "", ""

    @property
    def frozen_marker(self):
        """Exists from just before rndc freeze until the zones are thawed.

        A sync killed in between (SIGKILL, the OOM killer) leaves it behind, and the
        next sync thaws the zones it finds frozen.
        """
        return os.path.join(self.checkzone_dir, "zones-frozen")

    def frozen_since(self):
        """When a sync that never thawed froze the zones, or None."""
        try:
            return datetime.fromtimestamp(os.path.getmtime(self.frozen_marker))
        except FileNotFoundError:
            return None

    def freeze(self):
        """Stop dynamic updates and flush each dynamic zone's journal to its file.

        Must run before zone files are written: freeze dumps the zone BIND
        holds in memory, which would overwrite a file written earlier.
        """
        with open(self.frozen_marker, "w") as f:
            f.write(f"{os.getpid()}\n")
        return self.run_commands([self.freeze_command])

    def thaw(self):
        """Resume dynamic updates, which a frozen zone refuses (ACME dns-01 among them)."""
        result = self.run_commands([self.thaw_command])
        if result[0]:
            try:
                os.unlink(self.frozen_marker)
            except FileNotFoundError:
                pass
        return result

    def reload(self):
        """Load the written zone files and resume dynamic updates.

        Thaws even when the reload fails, and reports the first failure.
        """
        reloaded = self.run_commands([self.reload_command])
        thawed = self.thaw()
        return reloaded if not reloaded[0] else thawed

    def find_zone(self, name):
        for model in (Domain, Ip4Subnet, Ip6Subnet):
            try:
                return model.objects.get(domain_name=name)
            except model.DoesNotExist:
                pass
        return None

    def pending_zones(self):
        return [
            zone
            for zone in chain(
                Domain.objects.all(), Ip4Subnet.objects.all(), Ip6Subnet.objects.all()
            )
            if zone.domain_serial != zone.domain_active_serial or self.force
        ]

    def sync_zone(self, zone):
        zonetype = getattr(zone._meta, "verbose_name", None) or zone._meta.model_name

        try:
            with open(zone.domain_filename) as f:
                old = f.read()
        except OSError:
            old = ""

        # Dynamic updates (ACME dns-01 challenges) raise the serial in the
        # frozen file past the one mdb generated. Secondaries ignore a zone
        # whose serial does not increase.
        live_serial = self.read_serial(old)
        if live_serial is not None and live_serial >= zone.domain_serial:
            zone.domain_serial = live_serial + 1

        self.changes[zone.domain_name] = {
            "old_serial": zone.domain_active_serial,
            "new_serial": zone.domain_serial,
            "success": False,
            "errors": None,
            "diff": None,
        }

        print(
            f"updating {zonetype} {zone.domain_name} "
            f"[{zone.domain_active_serial:d} -> {zone.domain_serial:d}]"
        )

        # Normalize to BIND's canonical format so the on-disk file and our
        # generated content always use the same format.
        new = self.normalize_zone(zone, zone.zone_file_contents())

        self.changes[zone.domain_name]["diff"] = self.calculate_diff(new, old, zone)

        sys.stdout.write("\t- validating... ")
        status, output = self.check_zone(zone, new)
        if status != 0:
            sys.stdout.write("fail\n")
            self.changes[zone.domain_name]["errors"] = output
            return False

        sys.stdout.write("ok\n")
        sys.stdout.write("\t- writing zone file... ")

        if not self.debug:
            zonefile = zone.domain_filename
        else:
            zonefile = self.debug_dir + zone.domain_filename
            path = "/".join(zonefile.split("/")[:-1])
            os.path.isdir(path) or os.makedirs(path)

        self.write_zone_file(zonefile, new)

        if not self.debug:
            zone.domain_active_serial = zone.domain_serial
            zone.save()

        sys.stdout.write("ok\n")
        self.changes[zone.domain_name]["success"] = True
        return True

    def write_zone_file(self, path, contents):
        """Replace the file at path with contents, whole or not at all.

        named may read the file at any time, and a write in place could leave it half
        written. The new file takes the old one's owner and mode: bind owns the zone
        files, and this runs as root.
        """
        directory, name = os.path.split(path)
        fd, tmp = tempfile.mkstemp(dir=directory or ".", prefix=f".{name}.")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(contents)
                f.flush()
                os.fsync(f.fileno())
            try:
                st = os.stat(path)
            except FileNotFoundError:
                os.chmod(tmp, 0o644)
            else:
                os.chmod(tmp, stat.S_IMODE(st.st_mode))
                if (st.st_uid, st.st_gid) != (os.getuid(), os.getgid()):
                    os.chown(tmp, st.st_uid, st.st_gid)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    def read_serial(self, contents):
        """Return the SOA serial of a zone file, or None if there is none."""
        match = re.search(r"^\s*(\d+)\s*;\s*serial", contents, re.MULTILINE)
        return int(match.group(1)) if match else None

    def normalize_zone(self, zone, contents):
        """Convert zone file contents to BIND's canonical format.

        Uses named-compilezone to produce the same format that rndc freeze
        writes, so subsequent freeze/thaw cycles won't reformat the file and
        cause spurious diffs.  Falls back to the original contents if
        named-compilezone is unavailable or fails.
        """
        if not os.path.isfile(self.compilezone_bin):
            return contents

        with tempfile.NamedTemporaryFile(mode="w", suffix=".zone", delete=False) as f:
            f.write(contents)
            tmpfile = f.name

        try:
            cmd = f"{self.compilezone_bin} -f text -F text -s relative -i none -o - {zone.domain_name} {tmpfile}"
            status, output = getstatusoutput(cmd + " 2>/dev/null")
            if status == 0:
                return output
            return contents
        finally:
            os.unlink(tmpfile)

    def calculate_diff(self, new, old, zone):
        return "\n".join(
            context_diff(
                a=old.splitlines(),
                b=new.splitlines(),
                fromfile=str(zone.domain_active_serial) + "-" + zone.domain_name,
                tofile=str(zone.domain_serial) + "-" + zone.domain_name,
                lineterm="",
            )
        )

    def check_zone(self, zone, contents):
        zonefile = self.checkzone_dir + "/" + zone.domain_name
        with open(zonefile, "w") as f:
            f.write(contents)

        return getstatusoutput(f"{self.checkzone_bin} {zone.domain_name} {zonefile}")
