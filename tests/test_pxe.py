import pytest
from django.conf import settings
from django.contrib import messages
from django.core.management import call_command
from django.urls import reverse

from mdb.models import Host, Interface, OperatingSystem
from mdb.pxe import get_pxe_filename, render_pxelinux_cfg


@pytest.fixture
def db_with_fixtures(db):
    call_command("loaddata", "test_data", verbosity=0)


@pytest.fixture
def host(db_with_fixtures):
    return Host.objects.first()


@pytest.mark.django_db
def test_render_pxeconfig(host):
    interface = host.interface_set.exclude(ip4address__isnull=True).first()
    config = render_pxelinux_cfg(interface, host)

    assert settings.MDB_PXE_INITRD in config
    assert settings.MDB_PXE_KERNEL in config
    assert settings.MDB_PXE_PRESEED_URL in config


@pytest.mark.django_db
def test_render_pxeconfig_with_os_pxe_config(host):
    _os = OperatingSystem.objects.get(pk=2)  # OS with all pxe vars set
    Host.objects.filter(pk=host.pk).update(operating_system=_os)
    host = Host.objects.first()

    interface = host.interface_set.exclude(ip4address__isnull=True).first()
    config = render_pxelinux_cfg(interface, host)

    assert _os.pxe_initrd in config
    assert _os.pxe_kernel in config
    assert _os.pxe_preseed_config_url in config


@pytest.mark.django_db
def test_host_as_pxe_files(host):
    assert len(host.as_pxe_files()) == 1


PXE_FILE = "01-f0-de-f1-58-be-1a"  # from the fixture interface's MAC address


@pytest.fixture
def tftp_root(settings, tmp_path):
    settings.MDB_PXE_TFTP_ROOT = str(tmp_path)
    return tmp_path


def test_saving_installable_host_writes_pxe_file(host, tftp_root):
    Interface.objects.update(pxe_filename="", dhcp_client=False)
    host.save()

    path = tftp_root / PXE_FILE
    assert host.pxe_key in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o644
    # The interface is set up to boot from the network.
    interface = host.interface_set.get()
    assert interface.pxe_filename == "pxelinux.0"
    assert interface.dhcp_client


def test_saving_host_keeps_custom_pxe_filename(host, tftp_root):
    Interface.objects.update(pxe_filename="custom.efi")
    host.save()
    assert host.interface_set.get().pxe_filename == "custom.efi"


def test_saving_non_installable_host_deletes_pxe_file(host, tftp_root):
    (tftp_root / PXE_FILE).write_text("old")
    host.pxe_installable = False
    host.save()
    assert not (tftp_root / PXE_FILE).exists()


def test_saving_host_without_key_generates_one(host, tftp_root):
    host.pxe_key = ""
    host.save()
    key = Host.objects.get(pk=host.pk).pxe_key
    assert len(key) == 32
    assert key in (tftp_root / PXE_FILE).read_text()


def test_pxe_filename_by_ip_address(host):
    interface = host.interface_set.get()  # 10.0.3.2
    assert get_pxe_filename(interface, "ip_addr") == "0A000302"


def test_admin_marks_hosts_installable(host, tftp_root, admin_client):
    Host.objects.update(pxe_installable=False)

    res = admin_client.post(
        reverse("admin:mdb_host_changelist"),
        {"action": "set_installable", "_selected_action": [host.pk]},
        follow=True,
    )

    assert res.status_code == 200
    assert Host.objects.get(pk=host.pk).pxe_installable
    assert (tftp_root / PXE_FILE).exists()
    assert not [m for m in res.context["messages"] if m.level == messages.WARNING]


def test_admin_warns_about_interfaces_without_ip(host, tftp_root, admin_client):
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
