from difflib import context_diff
from subprocess import getstatusoutput

from mdb.models import DhcpConfig


class DhcpSyncService:
    restart_command = "/usr/sbin/service isc-dhcp-server restart"

    def __init__(self, force=False):
        self.force = force

    def get_config(self):
        return DhcpConfig.objects.filter(name="default").get()

    def needs_update(self, config):
        return config.serial != config.active_serial or self.force

    def calculate_diff(self, config, new, old):
        return "\n".join(
            context_diff(
                a=old.splitlines(),
                b=new.splitlines(),
                fromfile=str(config.active_serial),
                tofile=str(config.serial),
                lineterm="",
            )
        )

    def write_config(self, config, output_path):
        """Write new DHCP config to file and update active_serial.

        Returns (old_serial, diff).
        """
        try:
            with open(output_path, "r") as f:
                old = f.read()
        except IOError:
            old = ""

        new = config.dhcpd_configuration()
        with open(output_path, "w") as f:
            f.write(new)

        diff = self.calculate_diff(config, new, old)

        old_serial = config.active_serial
        config.active_serial = config.serial
        config.save()

        return old_serial, diff

    def restart_service(self):
        """Run the DHCP server restart command.

        Returns (success, output).
        """
        status, output = getstatusoutput(self.restart_command)
        return status == 0, output
