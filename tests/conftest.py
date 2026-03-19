import pytest
from django.core.management import call_command

from mdb.models import (
    Domain,
    DomainAAAARecord,
    DomainARecord,
    DomainCnameRecord,
    DomainTxtRecord,
    MailExchange,
    Nameserver,
)
from mdb.services.zone_sync import ZoneSyncService


@pytest.fixture
def domain(db):
    call_command("loaddata", "test_data", verbosity=0)
    return Domain.objects.get(domain_name="edb.technology")


@pytest.fixture
def service(tmp_path):
    svc = ZoneSyncService(debug=True)
    svc.checkzone_dir = str(tmp_path)
    return svc


@pytest.fixture
def db_domain(db, tmp_path):
    domain = Domain.objects.create(
        domain_name="example.org",
        domain_soa="ns1.example.org",
        domain_admin="admin@example.org",
        domain_ipaddr="1.2.3.4",
        domain_ip6addr="2001:db8::1",
        domain_filename=str(tmp_path / "db.example.org"),
        domain_ttl=3600,
        domain_serial=2024010101,
    )
    ns1 = Nameserver.objects.create(hostname="ns1.example.org")
    ns2 = Nameserver.objects.create(hostname="ns2.example.org")
    domain.domain_nameservers.set([ns1, ns2])
    mx = MailExchange.objects.create(priority=10, hostname="mail.example.org")
    domain.domain_mailexchanges.set([mx])
    DomainARecord.objects.create(domain=domain, name="ns1", target="1.2.3.4")
    DomainARecord.objects.create(domain=domain, name="ns2", target="5.6.7.8")
    DomainARecord.objects.create(domain=domain, name="mail", target="9.10.11.12")
    DomainARecord.objects.create(domain=domain, name="www", target="1.2.3.4")
    DomainAAAARecord.objects.create(domain=domain, name="www", target="2001:db8::1")
    DomainCnameRecord.objects.create(
        domain=domain, name="ftp", target="www.example.org."
    )
    DomainTxtRecord.objects.create(domain=domain, name="@", target='"v=spf1 mx ~all"')
    return domain


def load_command_class():
    path = pathlib.Path(__file__).parent.parent / "mdb/management/commands/zone-sync.py"
    spec = importlib.util.spec_from_file_location("zone_sync_command", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Command
