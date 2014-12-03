from __future__ import with_statement
from contextlib import closing

import os
import sys
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import mail_admins
from commands import getstatusoutput
from mdb.models import *


class Command(BaseCommand):
    args = '[--debug]'
    help = 'Generates the bind configuration'

    option_list = BaseCommand.option_list + (
        make_option('--debug',
                    action='store_true',
                    dest='force',
                    default=False,
                    help='Debug mode.'),
    )

    def handle(self, *args, **options):
        debug = options['debug']

        bind_init = "/etc/init.d/bind9 %s"

        error_log_file = "/tmp/zonecheck/zonecheck-fail-%s-%s"

        zone_check_command = "/usr/sbin/named-checkzone %s %s"
        zone_check_temp_dir = "/tmp/zonecheck"
        zone_check_temp_file = "%s/%s" % (zone_check_temp_dir, "zone")

        debug = False

        if not os.path.isfile((zone_check_command % ("", "")).strip()):
            print "ERROR: cannot find zone checking tool, exiting..."
            if not debug:
                sys.exit(1)

        if not os.path.isfile((bind_init % "").strip()):
            print "ERROR: cannot find bind init script, exiting..."
            if not debug:
                sys.exit(1)

        if not os.path.isdir(zone_check_temp_dir):
            os.mkdir(zone_check_temp_dir)

        reload_bind = False

        for domain in Domain.objects.all():
            if domain.domain_serial == domain.domain_active_serial and not debug:
                continue

            print "updating domain %s [%d -> %d]" % (
                domain.domain_name,
                domain.domain_active_serial,
                domain.domain_serial)

            sys.stdout.write("\t- validating...")
            zonecheck = open(zone_check_temp_file, "w")
            zonecheck.write(domain.zone_file_contents())
            zonecheck.close()

            result = check_zone(domain.domain_name, zone_check_temp_file)
            if result['value'] != 0:
                sys.stdout.write("fail\n")
                log = open(error_log_file % (
                    domain.domain_name,
                    domain.domain_serial), "w")
                log.write(domain.zone_file_contents())
                log.close()
                continue

            sys.stdout.write("ok\n")

            sys.stdout.write("\t- writing zone file...")
            zonefile = open(domain.domain_filename, "w")
            zonefile.write(domain.zone_file_contents())
            zonefile.close()
            sys.stdout.write("ok\n")

            reload_bind = True

            if not debug:
                domain.domain_active_serial = domain.domain_serial
                domain.save()

        for subnet in Ip4Subnet.objects.all():
            if subnet.domain_serial == subnet.domain_active_serial and not debug:
                continue
            print "updating subnet %s [%d -> %d]" % (
                subnet.domain_name,
                subnet.domain_active_serial,
                subnet.domain_serial)

            sys.stdout.write("\t- validating...")
            zonecheck = open(zone_check_temp_file, "w")
            zonecheck.write(subnet.zone_file_contents())
            zonecheck.close()
            sys.stdout.write("ok\n")

            result = check_zone(subnet.domain_name, zone_check_temp_file)
            if result['value'] != 0:
                sys.stdout.write("fail\n")
                log = open(error_log_file % (
                    subnet.domain_name,
                    subnet.domain_serial), "w")
                log.write(subnet.zone_file_contents())
                log.close()
                continue

            sys.stdout.write("\t- writing zone file...")
            zonefile = open(subnet.domain_filename, "w")
            zonefile.write(subnet.zone_file_contents())
            zonefile.close()
            sys.stdout.write("ok\n")

            reload_bind = True

            if not debug:
                subnet.domain_active_serial = subnet.domain_serial
                subnet.save()

        for subnet in Ip6Subnet.objects.all():
            if subnet.domain_serial == subnet.domain_active_serial and not debug:
                continue
            print "updating subnet %s [%d -> %d]" % (
                subnet.domain_name,
                subnet.domain_active_serial,
                subnet.domain_serial)

            sys.stdout.write("\t- validating...")
            zonecheck = open(zone_check_temp_file, "w")
            zonecheck.write(subnet.zone_file_contents())
            zonecheck.close()
            sys.stdout.write("ok\n")

            print subnet.zone_file_contents()

            result = check_zone(subnet.domain_name, zone_check_temp_file)
            if result['value'] != 0:
                sys.stdout.write("fail\n")
                log = open(error_log_file % (
                    subnet.domain_name,
                    subnet.domain_serial), "w")
                log.write(subnet.zone_file_contents())
                log.close()
                continue

            sys.stdout.write("\t- writing zone file...")
            zonefile = open(subnet.domain_filename, "w")
            zonefile.write(subnet.zone_file_contents())
            zonefile.close()
            sys.stdout.write("ok\n")

            reload_bind = True

            if not debug:
                subnet.domain_active_serial = subnet.domain_serial
                subnet.save()

        if reload_bind and not debug:
            sys.stdout.write("restarting bind...")
            status, output = getstatusoutput(bind_init % "reload")
            if status != 0:
                sys.stdout.write("fail\n")
                mail_admins(
                    "Failed to reload bind",
                    "Failed to reload bind, plase inspect...\n\n" + output)
            else:
                sys.stdout.write("ok\n")
                mail_admins(
                    "Successfully updated bind zone files",
                    "Bind zone files has been updated")


def check_zone(zone, filename):
    status, output = getstatusoutput(zone_check_command % (zone, filename))

    if debug and status != 0:
        print output

    return {'value': status, 'output': output}
