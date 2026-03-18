import os
import shutil
import sys
import tempfile
from difflib import context_diff
from itertools import chain
from subprocess import getstatusoutput

from mdb.models import Domain, Ip4Subnet, Ip6Subnet


class ZoneSyncService:
    rndc_bin = shutil.which("rndc") or "/usr/sbin/rndc"
    reload_command = "%s reload" % rndc_bin
    freeze_command = "%s freeze" % rndc_bin
    thaw_command = "%s thaw" % rndc_bin
    commands_in_order = [freeze_command, reload_command, thaw_command]
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
                print("ERROR: no such file %s, exiting..." % f)
                sys.exit(1)

    def run_reload_commands(self):
        """Execute freeze/reload/thaw in order.

        Returns (success, failed_command, output). On success, failed_command
        and output are empty strings.
        """
        for command in self.commands_in_order:
            status, output = getstatusoutput(command)
            if status != 0:
                return False, command, output
        return True, "", ""

    def find_zone(self, name):
        for model in (Domain, Ip4Subnet, Ip6Subnet):
            try:
                return model.objects.get(domain_name=name)
            except model.DoesNotExist:
                pass
        return None

    def sync_all_zones(self):
        for zone in chain(
            Domain.objects.all(), Ip4Subnet.objects.all(), Ip6Subnet.objects.all()
        ):
            if zone.domain_serial == zone.domain_active_serial and not self.force:
                continue
            if self.sync_zone(zone):
                self.changes[zone.domain_name]["success"] = True

    def sync_zone(self, zone):
        zonetype = getattr(zone._meta, "verbose_name", None) or zone._meta.model_name

        self.changes[zone.domain_name] = {
            "old_serial": zone.domain_active_serial,
            "new_serial": zone.domain_serial,
            "success": False,
            "errors": None,
            "diff": None,
        }

        print(
            "updating %s %s [%d -> %d]"
            % (
                zonetype,
                zone.domain_name,
                zone.domain_active_serial,
                zone.domain_serial,
            )
        )

        # Normalize to BIND's canonical format so the on-disk file and our
        # generated content always use the same format.
        new = self.normalize_zone(zone, zone.zone_file_contents())

        try:
            with open(zone.domain_filename, "r") as f:
                old = f.read()
        except IOError:
            old = ""

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

        with open(zonefile, "w") as f:
            f.write(new)

        if not self.debug:
            zone.domain_active_serial = zone.domain_serial
            zone.save()

        sys.stdout.write("ok\n")
        self.changes[zone.domain_name]["success"] = True
        return True

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
            cmd = "%s -f text -F text -s relative -i none -o - %s %s" % (
                self.compilezone_bin,
                zone.domain_name,
                tmpfile,
            )
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

        return getstatusoutput(
            "%s %s %s" % (self.checkzone_bin, zone.domain_name, zonefile)
        )
