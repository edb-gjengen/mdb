import pytest
from django.contrib import messages
from django.core.management import call_command
from django.urls import reverse

from mdb.models import Host, Interface


@pytest.fixture
def db_with_fixtures(db):
    call_command("loaddata", "test_data", verbosity=0)


@pytest.fixture
def host(db_with_fixtures):
    return Host.objects.first()


def test_saving_installable_host_boots_it_from_the_network(host):
    Interface.objects.update(pxe_filename="", dhcp_client=False)
    host.save()

    interface = host.interface_set.get()
    assert interface.pxe_filename == "pxelinux.0"
    assert interface.dhcp_client


def test_saving_host_keeps_custom_pxe_filename(host):
    Interface.objects.update(pxe_filename="custom.efi")
    host.save()
    assert host.interface_set.get().pxe_filename == "custom.efi"


def test_saving_non_installable_host_stops_netboot(host):
    Interface.objects.update(pxe_filename="pxelinux.0", dhcp_client=True)
    host.pxe_installable = False
    host.save()

    interface = host.interface_set.get()
    assert interface.pxe_filename == ""
    # The host keeps its address.
    assert interface.dhcp_client


def test_saving_non_installable_host_keeps_custom_pxe_filename(host):
    Interface.objects.update(pxe_filename="custom.efi")
    host.pxe_installable = False
    host.save()
    assert host.interface_set.get().pxe_filename == "custom.efi"


def test_saving_host_without_key_generates_one(host):
    host.pxe_key = ""
    host.save()
    assert len(Host.objects.get(pk=host.pk).pxe_key) == 32


def test_admin_marks_hosts_installable(host, admin_client):
    Host.objects.update(pxe_installable=False)
    Interface.objects.update(pxe_filename="")

    res = admin_client.post(
        reverse("admin:mdb_host_changelist"),
        {"action": "set_installable", "_selected_action": [host.pk]},
        follow=True,
    )

    assert res.status_code == 200
    assert Host.objects.get(pk=host.pk).pxe_installable
    assert host.interface_set.get().pxe_filename == "pxelinux.0"
    assert not [m for m in res.context["messages"] if m.level == messages.WARNING]


def test_admin_warns_about_interfaces_without_ip(host, admin_client):
    Host.objects.update(pxe_installable=False)
    Interface.objects.create(
        name="eth1", macaddr="00:11:22:33:44:55", host=host, domain_id=1
    )

    res = admin_client.post(
        reverse("admin:mdb_host_changelist"),
        {"action": "set_installable", "_selected_action": [host.pk]},
        follow=True,
    )

    warnings = [str(m) for m in res.context["messages"] if m.level == messages.WARNING]
    assert warnings == [
        "Host tut might not be installable since interface(s) eth1 has no IP set."
    ]
    assert Host.objects.get(pk=host.pk).pxe_installable
