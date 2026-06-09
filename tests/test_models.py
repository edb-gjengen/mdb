import pytest

from mdb.models import Ip4Subnet, Ip6Subnet


@pytest.mark.parametrize(
    "network,netmask,expected",
    [
        # /24 and shorter -> standard octet-boundary name
        ("203.0.113.0", "255.255.255.0", "113.0.203.in-addr.arpa"),
        ("10.0.3.0", "255.255.255.0", "3.0.10.in-addr.arpa"),
        ("10.0.0.0", "255.255.0.0", "0.0.10.in-addr.arpa"),
        # longer than /24 -> RFC 2317 classless name
        ("192.0.2.192", "255.255.255.192", "192-26.2.0.192.in-addr.arpa"),
        ("10.0.0.0", "255.255.255.252", "0-30.0.0.10.in-addr.arpa"),
        ("10.1.2.0", "255.255.255.128", "0-25.2.1.10.in-addr.arpa"),
        # host bits set -> normalized down to the network address
        ("192.0.2.200", "255.255.255.192", "192-26.2.0.192.in-addr.arpa"),
    ],
)
def test_ip4_reverse_zone_name(network, netmask, expected):
    subnet = Ip4Subnet(network=network, netmask=netmask)
    assert subnet.reverse_zone_name == expected


@pytest.mark.parametrize(
    "network,netmask,expected",
    [
        ("2001:db8", 64, "0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2.ip6.arpa"),
        ("2001:db8", 48, "0.0.0.0.8.b.d.0.1.0.0.2.ip6.arpa"),
        ("2001:db8:abcd", 56, "0.0.d.c.b.a.8.b.d.0.1.0.0.2.ip6.arpa"),
        ("2001:db8", 32, "8.b.d.0.1.0.0.2.ip6.arpa"),
    ],
)
def test_ip6_reverse_zone_name(network, netmask, expected):
    subnet = Ip6Subnet(network=network, netmask=netmask)
    assert subnet.reverse_zone_name == expected
