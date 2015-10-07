import logging
import os
import uuid
from django.conf import settings
from django.db.models.signals import pre_delete, post_save, pre_save
from django.dispatch import receiver
import ipaddress

from mdb.models import Interface, Host, Ip6Subnet, Ip4Subnet, Ip4Address
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
        ipspl = instance.network.split(".")
        rev = "%s.%s.%s" % (ipspl[2], ipspl[1], ipspl[0])
        instance.domain_name = "%s.in-addr.arpa" % rev

    # update it's own serial
    # if instance.domain_serial is not None:
    #     instance.domain_serial = format_domain_serial_and_add_one(instance.domain_serial)

    # lets update the serial of the dhcp config
    # when the subnet is changed
    if instance.dhcp_config:
        # instance.dhcp_config.serial = instance.dhcp_config.serial + 1
        instance.dhcp_config.serial = format_domain_serial_and_add_one(instance.dhcp_config.serial)
        instance.dhcp_config.save()


@receiver(pre_save, sender=Ip6Subnet)
def set_domain_name_for_ipv6_subnet(sender, instance, **kwargs):
    if len(instance.domain_name) > 0:
        return

    network = ipaddress.IPv6Address("%s::" % instance.network)
    instance.domain_name = ".".join(network.exploded.replace(":", "")[:16])[::-1] + ".ip6.arpa"


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
            domain.domain_serial = format_domain_serial_and_add_one(domain.domain_serial)
            domain.save()
        if interface.ip4address is not None:
            subnet = interface.ip4address.subnet
            subnet.domain_serial = format_domain_serial_and_add_one(subnet.domain_serial)
            subnet.save()


@receiver(post_save, sender=Host)
def create_pxe_key_and_write_pxe_files_when_host_changes(sender, instance, created, **kwargs):
    host = instance

    if not host.pxe_key:
        # generate key (prevent infinite recursion by using update)
        pxe_key = uuid.uuid4().hex
        Host.objects.filter(pk=host.pk).update(pxe_key=pxe_key)
        host.pxe_key = pxe_key

    for pxe_file_name, pxe_file in host.as_pxe_files():
        path = os.path.join(settings.MDB_PXE_TFTP_ROOT, pxe_file_name)
        if host.pxe_installable:
            with open(path, 'w+') as f:
                f.write(pxe_file)
                logger.info("Created or updated {}".format(path))

            # Also set necessary fields for pxe installation
            interfaces = host.interface_set.exclude(ip4address__isnull=True)

            for _if in interfaces:
                changed = False
                if not _if.pxe_filename:
                    _if.pxe_filename = 'pxelinux.0'  # don't overwrite
                    changed = True
                if not _if.dhcp_client:
                    _if.dhcp_client = True
                    changed = True

                if changed:
                    _if.save()

        else:
            if os.path.exists(path):
                os.unlink(path)
                logger.info("deleted {}".format(path))


@receiver(pre_delete, sender=Interface)
def update_domain_serial_when_interface_deleted(sender, instance, **kwargs):
    if instance.domain is not None:
        domain = instance.domain
        domain.domain_serial += 1
        domain.save()

    if instance.ip4address is not None:
        subnet = instance.ip4address.subnet
        subnet.domain_serial += 1
        subnet.save()

# @receiver(pre_save, sender=Domain)
# def update_domain_serial_when_domain_is_saved(sender, instance, **kwargs):
#    instance.domain_serial = format_domain_serial_and_add_one(instance.domain_serial)
