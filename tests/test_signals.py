import pytest

from mdb.models import DhcpConfig, Ip4Subnet, Ip6Subnet

# ---------------------------------------------------------------------------
# pre_save signals: populate domain_name once, then leave it frozen
# ---------------------------------------------------------------------------


def make_ip4subnet(**overrides):
    dhcp_config = DhcpConfig.objects.create(serial=1, active_serial=1)
    fields = {
        "name": "test-subnet",
        "netmask": "255.255.255.192",
        "network": "192.0.2.192",
        "domain_soa": "ns1.example.org",
        "domain_admin": "admin@example.org",
        "domain_filename": "db.test-subnet",
        "dhcp_config": dhcp_config,
    }
    fields.update(overrides)
    return Ip4Subnet.objects.create(**fields)


@pytest.mark.django_db
def test_ip4_signal_sets_classless_domain_name():
    subnet = make_ip4subnet()
    assert subnet.domain_name == "192-26.2.0.192.in-addr.arpa"


@pytest.mark.django_db
def test_ip4_signal_sets_plain_domain_name_for_slash24():
    subnet = make_ip4subnet(network="203.0.113.0", netmask="255.255.255.0")
    assert subnet.domain_name == "113.0.203.in-addr.arpa"


@pytest.mark.django_db
def test_ip4_signal_does_not_overwrite_existing_domain_name():
    subnet = make_ip4subnet(domain_name="manual.in-addr.arpa")
    assert subnet.domain_name == "manual.in-addr.arpa"


@pytest.mark.django_db
def test_ip4_domain_name_is_frozen_when_network_changes():
    subnet = make_ip4subnet()
    assert subnet.domain_name == "192-26.2.0.192.in-addr.arpa"

    subnet.network = "10.0.0.0"
    subnet.netmask = "255.255.255.0"
    subnet.save()
    subnet.refresh_from_db()

    # The name is derived once and then left alone.
    assert subnet.domain_name == "192-26.2.0.192.in-addr.arpa"


@pytest.mark.django_db
def test_ip6_signal_sets_domain_name():
    subnet = Ip6Subnet.objects.create(
        name="ipv6-doc",
        network="2001:db8",
        netmask=64,
        domain_soa="ns1.example.org",
        domain_admin="admin@example.org",
        domain_filename="db.reverse-v6",
    )
    assert subnet.domain_name == "0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2.ip6.arpa"
