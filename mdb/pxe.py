from django.conf import settings
from django.template.loader import render_to_string
import ipaddress


def render_pxelinux_cfg(_if, host):
    """Renders pxelinux.cfg based on a host and the set of host interfaces.
    If the host is tied to an OS with PXE fields set, it will use these instead of defaults."""
    # Default config
    kernel = settings.MDB_PXE_KERNEL
    initrd = settings.MDB_PXE_INITRD
    preseed_config_url = settings.MDB_PXE_PRESEED_URL

    # Per host config (via OS model)
    _os = host.operating_system
    pxe_attrs = [_os.pxe_initrd, _os.pxe_kernel, _os.pxe_preseed_config_url]
    if None not in pxe_attrs and '' not in pxe_attrs:
        kernel = _os.pxe_kernel
        initrd = _os.pxe_initrd
        preseed_config_url = _os.pxe_preseed_config_url

    context = {
        'kernel': kernel,
        'initrd': initrd,
        'preseed_config_url': preseed_config_url,
        'host': host,
        'interface': _if
    }

    return render_to_string('pxelinux.cfg', context=context)


def get_pxe_filename(interface, filename_format='mac_addr'):
    """
    Mac or IP address based PXE filename
    Ref: http://www.syslinux.org/wiki/index.php/PXELINUX#Examples
    """
    ip_addr_in_hex = '{:02X}'.format(int(ipaddress.IPv4Address(interface.ip4address.address)))
    formats = {
        'ip_addr': ip_addr_in_hex,
        'mac_addr': '01-{}'.format(interface.macaddr.lower().replace(':', '-'))
    }

    return formats.get(filename_format, formats['mac_addr'])


def host_as_pxe_files(host):
    """Returns a list of filename,content for each host interface with an IPv4 address."""
    from mdb.models import Host
    assert isinstance(host, Host)

    pxe_files = []
    for _if in host.interface_set.exclude(ip4address__isnull=True):
        filename = get_pxe_filename(_if)
        content = render_pxelinux_cfg(_if, host)
        pxe_files.append((filename, content))

    return pxe_files
