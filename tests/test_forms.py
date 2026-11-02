import pytest
from django.core.management import call_command

from mdb.forms import InterfaceForm
from mdb.models import Host, Interface, Ip4Address


@pytest.fixture
def fixtures(db):
    call_command("loaddata", "test_data", verbosity=0)


def form(instance=None, **overrides):
    data = {
        "name": "eth1",
        "macaddr": "00:11:22:33:44:55",
        "host": Host.objects.get().pk,
        "domain": 1,
        "ip4address": Ip4Address.objects.get(address="10.0.3.10").pk,
        "pxe_filename": "",
    } | overrides
    return InterfaceForm(data=data, instance=instance)


def test_valid(fixtures):
    f = form()
    assert f.is_valid(), f.errors


def test_invalid_mac_is_a_form_error(fixtures):
    # Used to raise KeyError, a 500 in the admin.
    f = form(macaddr="not a mac")
    assert not f.is_valid()
    assert "macaddr" in f.errors


def test_interface_without_ip4address(fixtures):
    f = form(ip4address="")
    assert f.is_valid(), f.errors


@pytest.mark.parametrize("macaddr", ["f0:de:f1:58:be:1a", "F0:DE:F1:58:BE:1A"])
def test_mac_already_in_subnet(fixtures, macaddr):
    f = form(macaddr=macaddr)
    assert not f.is_valid()
    assert f.non_field_errors() == ["Macaddr already in this subnet"]


def test_mac_in_use_by_interface_without_ip4address(fixtures):
    # Used to raise AttributeError on the other interface's missing address.
    Interface.objects.update(ip4address=None)
    f = form(macaddr="f0:de:f1:58:be:1a")
    assert f.is_valid(), f.errors


def test_editing_interface_does_not_clash_with_itself(fixtures):
    interface = Interface.objects.get()
    f = form(
        instance=interface,
        name="eth0",
        macaddr=interface.macaddr,
        ip4address=interface.ip4address.pk,
    )
    assert f.is_valid(), f.errors
