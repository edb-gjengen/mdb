import pytest
from django.conf import settings
from django.core.management import call_command

from mdb.models import Host, OperatingSystem
from mdb.pxe import render_pxelinux_cfg


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
