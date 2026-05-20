import os
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

from mdb.models import (
    DhcpConfig,
    Host,
    HostType,
    Interface,
    Ip4Subnet,
    OperatingSystem,
)
from mdb.services.zone_sync import ZoneSyncService

EXPECTED_ZONE_FILE_CONTENTS = """\
; serial:2024010101
; zone file for example.org
; 2024-01-01 00:00:00
; filename: {filename}
$TTL 3600
@ IN SOA ns1.example.org. admin.example.org. (
\t2024010101\t; serial
\t28800\t; refresh
\t7200\t; retry
\t604800\t; expire
\t86400 )\t; minimum ttl
;
@\tIN\tNS\tns1.example.org.
@\tIN\tNS\tns2.example.org.
@\t\tMX\t10 mail.example.org.
@\tIN\tA\t1.2.3.4
@\tIN\tAAAA\t2001:db8::1
; SRV records
; A records
ns1 IN A 1.2.3.4
ns2 IN A 5.6.7.8
mail IN A 9.10.11.12
www IN A 1.2.3.4
; AAAA records
www IN AAAA 2001:db8::1
; CNAME records \nftp\tIN\tCNAME\twww.example.org.
; TXT records \n@ TXT "v=spf1 mx ~all"
; HOST records
"""

EXPECTED_NORMALIZED = (
    "$TTL 3600\t; 1 hour\n"
    "example.org.\t\tIN SOA\tns1.example.org. admin.example.org. (\n"
    "\t\t\t\t2024010101 ; serial\n"
    "\t\t\t\t28800      ; refresh (8 hours)\n"
    "\t\t\t\t7200       ; retry (2 hours)\n"
    "\t\t\t\t604800     ; expire (1 week)\n"
    "\t\t\t\t86400      ; minimum (1 day)\n"
    "\t\t\t\t)\n"
    "\t\t\tNS\tns1.example.org.\n"
    "\t\t\tNS\tns2.example.org.\n"
    "\t\t\tA\t1.2.3.4\n"
    "\t\t\tMX\t10 mail.example.org.\n"
    '\t\t\tTXT\t"v=spf1 mx ~all"\n'
    "\t\t\tAAAA\t2001:db8::1\n"
    "ftp.example.org.\tCNAME\twww.example.org.\n"
    "mail.example.org.\tA\t9.10.11.12\n"
    "ns1.example.org.\tA\t1.2.3.4\n"
    "ns2.example.org.\tA\t5.6.7.8\n"
    "www.example.org.\tA\t1.2.3.4\n"
    "\t\t\tAAAA\t2001:db8::1"
)


SAMPLE_ZONE = """\
$TTL 3600
example.com. IN SOA ns1.example.com. admin.example.com. (
    2024010101 ; serial
    3600       ; refresh
    900        ; retry
    604800     ; expire
    86400      ; minimum
)
example.com.        IN NS    ns1.example.com.
example.com.        IN NS    ns2.example.com.
example.com.        IN MX    10 mail.example.com.
example.com.        IN MX    20 mail2.example.com.
example.com.        IN A     1.2.3.4
example.com.        IN AAAA  2001:db8::1
example.com.        IN TXT   "v=spf1 mx ~all"
ns1.example.com.    IN A     1.2.3.4
ns2.example.com.    IN A     5.6.7.8
mail.example.com.   IN A     9.10.11.12
www.example.com.    IN CNAME example.com.
_dmarc.example.com. IN TXT   "v=DMARC1; p=none; rua=mailto:dmarc@example.com"
"""


def make_zone(domain_name="example.com", active_serial=2024010101, serial=2024010102):
    zone = MagicMock()
    zone.domain_name = domain_name
    zone.domain_active_serial = active_serial
    zone.domain_serial = serial
    return zone


def test_calculate_diff_identical_returns_empty(service):
    zone = make_zone()
    assert service.calculate_diff("line\n", "line\n", zone) == ""


def test_calculate_diff_format(service):
    zone = make_zone(domain_name="example.com", active_serial=1, serial=2)
    diff = service.calculate_diff("new line\n", "old line\n", zone)
    assert "*** 1-example.com" in diff
    assert "--- 2-example.com" in diff
    assert "! old line" in diff
    assert "! new line" in diff


def test_normalize_zone_is_idempotent(service):
    zone = make_zone()
    normalized = service.normalize_zone(zone, SAMPLE_ZONE)
    assert service.normalize_zone(zone, normalized) == normalized


def test_normalize_zone_fallback_when_binary_missing(service):
    service.compilezone_bin = "/nonexistent/named-compilezone"
    zone = make_zone()
    assert service.normalize_zone(zone, SAMPLE_ZONE) == SAMPLE_ZONE


def test_check_zone_valid(service):
    zone = make_zone()
    status, _ = service.check_zone(zone, SAMPLE_ZONE)
    assert status == 0


def test_check_zone_invalid(service):
    zone = make_zone()
    status, _ = service.check_zone(zone, "this is not a valid zone file")
    assert status != 0


@freeze_time("2024-01-01 00:00:00")
def test_zone_file_contents_includes_all_record_types(db_domain):
    content = db_domain.zone_file_contents()
    assert content == EXPECTED_ZONE_FILE_CONTENTS.format(
        filename=db_domain.domain_filename
    )


def test_zone_file_contents_normalizes_without_error(db_domain, service):
    normalized = service.normalize_zone(db_domain, db_domain.zone_file_contents())
    assert normalized == EXPECTED_NORMALIZED


def test_check_zone_accepts_zone_file_contents(db_domain, service):
    content = service.normalize_zone(db_domain, db_domain.zone_file_contents())
    status, output = service.check_zone(db_domain, content)
    assert status == 0, output
    assert "loaded serial 2024010101" in output
    assert output.endswith("OK")


def test_find_zone_returns_matching_domain(db_domain, service):
    assert service.find_zone("example.org") == db_domain


@pytest.mark.django_db
def test_find_zone_returns_none_for_unknown(service):
    assert service.find_zone("nonexistent.example") is None


def test_sync_zone_writes_zone_file_and_updates_serial(db_domain, tmp_path):
    svc = ZoneSyncService(debug=False)
    svc.checkzone_dir = str(tmp_path)

    svc.sync_zone(db_domain)

    assert os.path.exists(db_domain.domain_filename)
    db_domain.refresh_from_db()
    assert db_domain.domain_active_serial == db_domain.domain_serial


def test_sync_zone_records_success_and_diff(db_domain, tmp_path):
    svc = ZoneSyncService(debug=False)
    svc.checkzone_dir = str(tmp_path)

    svc.sync_zone(db_domain)

    change = svc.changes["example.org"]
    assert change["success"] is True
    assert change["errors"] is None
    assert change["old_serial"] == 0
    assert change["new_serial"] == 2024010101


def add_host(domain, hostname, allow_email, ip4address=None):
    host_type = HostType.objects.create(host_type="server", description="")
    operating_system = OperatingSystem.objects.create(
        name="Debian", version="12", arch="x86_64"
    )
    host = Host.objects.create(
        hostname=hostname,
        host_type=host_type,
        operating_system=operating_system,
        allow_email=allow_email,
    )
    Interface.objects.create(
        name="eth0",
        macaddr="00:11:22:33:44:55",
        host=host,
        domain=domain,
        ip4address=ip4address,
    )
    # Creating the interface bumps the domain serial via a signal; reload so the
    # in-memory domain stays consistent with the DB.
    domain.refresh_from_db()
    return host


def make_ip4address():
    """Create a tiny (/30) subnet; its post_save signal generates the host IPs."""
    dhcp_config = DhcpConfig.objects.create(serial=1, active_serial=1)
    subnet = Ip4Subnet.objects.create(
        name="test-subnet",
        netmask="255.255.255.252",
        network="10.0.0.0",
        domain_soa="ns1.example.org",
        domain_admin="admin@example.org",
        domain_filename="db.test-subnet",
        dhcp_config=dhcp_config,
    )
    return subnet.ip4address_set.get(address="10.0.0.1")


def test_zone_file_contents_includes_spf_record_when_email_allowed(db_domain):
    add_host(db_domain, "mailhost", allow_email=True)
    content = db_domain.zone_file_contents()
    assert 'mailhost\tTXT\t"v=spf1 mx -all"\n' in content


def test_zone_file_contents_omits_spf_record_when_email_not_allowed(db_domain):
    add_host(db_domain, "plainhost", allow_email=False)
    content = db_domain.zone_file_contents()
    assert "v=spf1 mx -all" not in content


def test_zone_file_contents_includes_ip4_in_spf_record_when_interface_has_address(
    db_domain,
):
    address = make_ip4address()
    add_host(db_domain, "mailhost", allow_email=True, ip4address=address)
    content = db_domain.zone_file_contents()
    assert f'mailhost\tTXT\t"v=spf1 mx ip4:{address.address} -all"\n' in content
