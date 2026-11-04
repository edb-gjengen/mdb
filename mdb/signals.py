import ipaddress
import logging
import uuid

from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from mdb.models import PXE_FILENAME, Host, Interface, Ip4Address, Ip4Subnet, Ip6Subnet
from mdb.utils import format_domain_serial_and_add_one

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Ip4Subnet)
def create_ips_for_subnet(sender, instance, created, **kwargs):
    if not created:
        return

    subnet = ipaddress.IPv4Network(instance.network + "/" + instance.netmask)

    for addr in subnet.hosts():
        address = Ip4Address(address=str(addr), subnet=instance)
        address.save()


@receiver(pre_delete, sender=Ip4Subnet)
def delete_ips_for_subnet(sender, instance, **kwargs):
    for addr in instance.ip4address_set.all():
        addr.delete()


@receiver(pre_save, sender=Ip4Subnet)
def set_domain_name_for_subnet(sender, instance, **kwargs):
    # we assume that the reverse domain_name does not change
    if len(instance.domain_name) == 0:
        instance.domain_name = instance.reverse_zone_name

    # update it's own serial
    # if instance.domain_serial is not None:
    #     instance.domain_serial = format_domain_serial_and_add_one(instance.domain_serial)

    # lets update the serial of the dhcp config
    # when the subnet is changed
    if instance.dhcp_config:
        # instance.dhcp_config.serial = instance.dhcp_config.serial + 1
        instance.dhcp_config.serial = format_domain_serial_and_add_one(
            instance.dhcp_config.serial
        )
        instance.dhcp_config.save()


@receiver(pre_save, sender=Ip6Subnet)
def set_domain_name_for_ipv6_subnet(sender, instance, **kwargs):
    if len(instance.domain_name) > 0:
        return

    instance.domain_name = instance.reverse_zone_name


@receiver(post_save, sender=Interface)
def update_domain_serial_when_change_to_interface(sender, instance, created, **kwargs):
    if instance.domain is not None:
        domain = instance.domain
        domain.domain_serial = format_domain_serial_and_add_one(domain.domain_serial)
        domain.save()

    if instance.ip4address is not None:
        subnet = instance.ip4address.subnet
        subnet.domain_serial = format_domain_serial_and_add_one(subnet.domain_serial)
        subnet.save()


@receiver(post_save, sender=Host)
def update_domain_serial_when_change_to_host(sender, instance, created, **kwargs):
    for interface in instance.interface_set.all():
        if interface.domain is not None:
            domain = interface.domain
            domain.domain_serial = format_domain_serial_and_add_one(
                domain.domain_serial
            )
            domain.save()
        if interface.ip4address is not None:
            subnet = interface.ip4address.subnet
            subnet.domain_serial = format_domain_serial_and_add_one(
                subnet.domain_serial
            )
            subnet.save()


@receiver(post_save, sender=Host)
def set_pxe_boot_when_host_changes(sender, instance, created, **kwargs):
    """An installable host netboots into the menu; unticking it stops that.
    A filename other than pxelinux's is left alone either way."""
    host = instance

    if not host.pxe_key:
        # generate key (prevent infinite recursion by using update)
        pxe_key = uuid.uuid4().hex
        Host.objects.filter(pk=host.pk).update(pxe_key=pxe_key)
        host.pxe_key = pxe_key

    for _if in host.interface_set.exclude(ip4address__isnull=True):
        changed = False
        if host.pxe_installable:
            if not _if.pxe_filename:
                _if.pxe_filename = PXE_FILENAME
                changed = True
            if not _if.dhcp_client:
                _if.dhcp_client = True
                changed = True
        elif _if.pxe_filename == PXE_FILENAME:
            _if.pxe_filename = ""
            changed = True
        if changed:
            _if.save()


@receiver(pre_delete, sender=Interface)
def update_domain_serial_when_interface_deleted(sender, instance, **kwargs):
    if instance.domain is not None:
        domain = instance.domain
        domain.domain_serial = format_domain_serial_and_add_one(domain.domain_serial)
        domain.save()

    if instance.ip4address is not None:
        subnet = instance.ip4address.subnet
        subnet.domain_serial = format_domain_serial_and_add_one(subnet.domain_serial)
        subnet.save()


# @receiver(pre_save, sender=Domain)
# def update_domain_serial_when_domain_is_saved(sender, instance, **kwargs):
#    instance.domain_serial = format_domain_serial_and_add_one(instance.domain_serial)
