import datetime
import ipaddress

from django.db import models
from django.utils.translation import gettext_lazy as _

from mdb.validators import validate_hostname, validate_macaddr

# The boot file of a PXE installable host. UEFI x86-64 clients, PXE architecture 7 or 9
# in their vendor class, get the UEFI loader instead.
PXE_FILENAME = "pxelinux.0"
PXE_EFI_FILENAME = "grubx64.efi"
PXE_EFI_CLIENT = " or ".join(
    f'substring(option vendor-class-identifier, 0, 20) = "PXEClient:Arch:{arch}"'
    for arch in ("00007", "00009")
)


class Nameserver(models.Model):
    hostname = models.CharField(max_length=256)

    def __str__(self):
        return self.hostname


class MailExchange(models.Model):
    priority = models.IntegerField()
    hostname = models.CharField(max_length=256)

    def __str__(self):
        return "(" + str(self.priority) + ") " + self.hostname


class Domain(models.Model):
    domain_name = models.CharField(max_length=256)
    domain_soa = models.CharField(max_length=256)
    domain_ttl = models.IntegerField(default=60)
    domain_serial = models.IntegerField(default=1)
    domain_active_serial = models.IntegerField(default=0, editable=False)
    domain_refresh = models.IntegerField(default=28800)
    domain_retry = models.IntegerField(default=7200)
    domain_expire = models.IntegerField(default=604800)
    domain_minimum_ttl = models.IntegerField(default=86400)
    domain_admin = models.EmailField()
    domain_ipaddr = models.GenericIPAddressField(protocol="IPv4")
    domain_ip6addr = models.GenericIPAddressField(
        protocol="IPv6", blank=True, null=True
    )
    domain_filename = models.CharField(max_length=256)
    created_date = models.DateTimeField(auto_now_add=True)

    domain_nameservers = models.ManyToManyField(Nameserver)
    domain_mailexchanges = models.ManyToManyField(MailExchange)

    def __str__(self):
        return self.domain_name

    def __eq__(self, other):
        if not other or not hasattr(other, "domain_name"):
            return False

        return self.domain_name == other.domain_name

    def zone_file_contents(self):
        content = f"; serial:{self.domain_serial:d}\n"
        content += f"; zone file for {self.domain_name}\n"
        content += f"; {datetime.datetime.now()}\n"
        content += f"; filename: {self.domain_filename}\n"
        content += f"$TTL {self.domain_ttl}\n"
        content += "@ IN SOA {}. {}. (\n".format(
            self.domain_soa,
            self.domain_admin.replace("@", "."),
        )
        content += f"\t{self.domain_serial:d}\t; serial\n"
        content += f"\t{self.domain_refresh:d}\t; refresh\n"
        content += f"\t{self.domain_retry:d}\t; retry\n"
        content += f"\t{self.domain_expire:d}\t; expire\n"
        content += f"\t{self.domain_minimum_ttl:d} )\t; minimum ttl\n"
        content += ";\n"

        for nameserver in self.domain_nameservers.all():
            content += f"@\tIN\tNS\t{nameserver.hostname}.\n"

        for mx in self.domain_mailexchanges.all():
            content += f"@\t\tMX\t{mx.priority:d} {mx.hostname}.\n"

        if self.domain_ipaddr is not None:
            content += f"@\tIN\tA\t{self.domain_ipaddr}\n"

        if self.domain_ip6addr:
            content += f"@\tIN\tAAAA\t{self.domain_ip6addr}\n"

        content += "; SRV records\n"

        for srv in self.domainsrvrecord_set.all():
            content += srv.as_record() + "\n"

        content += "; A records\n"

        for a in self.domainarecord_set.all():
            content += a.as_record() + "\n"

        content += "; AAAA records\n"

        for aaaa in self.domainaaaarecord_set.all():
            content += aaaa.as_record() + "\n"

        content += "; CNAME records \n"

        for cname in self.domaincnamerecord_set.all():
            content += f"{cname.name}\tIN\tCNAME\t{cname.target}\n"

        content += "; TXT records \n"

        for txt in self.domaintxtrecord_set.all():
            content += txt.as_record() + "\n"

        content += "; HOST records\n"

        for interface in self.interface_set.all():
            host = interface.host
            if interface.ip4address:
                content += (
                    f"{host.hostname:<20}\tIN\tA\t{interface.ip4address.address}\n"
                )

            for ipv6addr in interface.ip6address_set.all():
                content += f"{host.hostname:<20}\tIN\tAAAA\t{ipv6addr.full_address()}\n"

            if host.allow_email and interface.ip4address:
                content += f'{host.hostname}\tTXT\t"v=spf1 mx ip4:{interface.ip4address.address} -all"\n'
            elif host.allow_email:
                content += f'{host.hostname}\tTXT\t"v=spf1 mx -all"\n'

        return content


class DomainSrvRecord(models.Model):
    srvce = models.CharField(max_length=64)
    prot = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    priority = models.IntegerField()
    weight = models.IntegerField()
    port = models.IntegerField()
    target = models.CharField(max_length=256)
    domain = models.ForeignKey(Domain, models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)

    def as_record(self):
        return f"{self.srvce}.{self.prot}.{self.name}. IN SRV {self.priority} {self.weight} {self.port} {self.target}."

    def __str__(self):
        return self.as_record()


class DomainTxtRecord(models.Model):
    name = models.CharField(max_length=256)
    # note that the max length of a TXT record is 255, but
    # bind allows for longer records by splitting them
    # into chunks as: "...255..." "...another 255..."
    target = models.CharField(max_length=2048)
    domain = models.ForeignKey(Domain, models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)

    def as_record(self):
        return f"{self.name} TXT {self.target}"

    def __str__(self):
        return self.as_record()


class DomainCnameRecord(models.Model):
    name = models.CharField(max_length=256)
    target = models.CharField(max_length=256)
    domain = models.ForeignKey(Domain, models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)

    def as_record(self):
        return f"{self.name} IN CNAME {self.target}"

    def __str__(self):
        return self.as_record()


class DomainARecord(models.Model):
    name = models.CharField(max_length=256)
    target = models.GenericIPAddressField(protocol="IPv4")
    domain = models.ForeignKey(Domain, models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)

    def as_record(self):
        return f"{self.name} IN A {self.target}"

    def __str__(self):
        return self.as_record()


class DomainAAAARecord(models.Model):
    name = models.CharField(max_length=256)
    target = models.GenericIPAddressField(protocol="IPv6")
    domain = models.ForeignKey(Domain, models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)

    def as_record(self):
        return f"{self.name} IN AAAA {self.target}"

    def __str__(self):
        return self.as_record()


class DhcpConfig(models.Model):
    serial = models.IntegerField()
    active_serial = models.IntegerField()
    name = models.CharField(max_length=255)
    authoritative = models.BooleanField(default=False)
    ddns_update_style = models.CharField(max_length=63)
    default_lease_time = models.IntegerField(default=600)
    max_lease_time = models.IntegerField(default=7200)
    log_facility = models.CharField(max_length=255)

    def dhcpd_configuration(self):
        content = f"# Autogenerated configuration {datetime.datetime.now()}\n"
        if self.authoritative:
            content += "authoritative;\n"
        content += f"default-lease-time {self.default_lease_time:d};\n"
        content += f"max-lease-time {self.max_lease_time:d};\n"
        content += f"log-facility {self.log_facility};\n"
        content += f"ddns-update-style {self.ddns_update_style};\n"

        # time to write the subnet definitions
        for subnet in self.ip4subnet_set.all():
            content += f"\n# {subnet.name}\n"
            content += f"subnet {subnet.network} netmask {subnet.netmask} {{\n"

            for option in subnet.dhcpoption_set.all():
                content += f"\toption {option.key} {option.value};\n"

            for option in subnet.dhcpcustomfield_set.all():
                content += f"\t{option.value};\n"

            if subnet.dhcp_dynamic:
                content += (
                    f"\trange {subnet.dhcp_dynamic_start} {subnet.dhcp_dynamic_end};\n"
                )

            content += "}\n"

        # time to write host definitions
        for subnet in self.ip4subnet_set.all():
            for ip4address in subnet.ip4address_set.all():
                if (
                    not hasattr(ip4address, "interface")
                    or not ip4address.interface.dhcp_client
                ):
                    continue
                _if = ip4address.interface
                content += f"\nhost {_if.host.hostname} {{\n"
                content += f"\thardware ethernet {_if.macaddr};\n"
                content += (
                    f"\tfixed-address {_if.host.hostname}.{_if.domain.domain_name};\n"
                )
                if _if.pxe_filename == PXE_FILENAME:
                    content += (
                        f"\tif {PXE_EFI_CLIENT} {{\n"
                        f'\t\tfilename "{PXE_EFI_FILENAME}";\n'
                        "\t} else {\n"
                        f'\t\tfilename "{PXE_FILENAME}";\n'
                        "\t}\n"
                    )
                elif _if.pxe_filename:
                    content += f'\tfilename "{_if.pxe_filename}";\n'
                content += "}\n"

        return content

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "DHCP config"


class Ip6Subnet(models.Model):
    name = models.CharField(max_length=255)
    network = models.CharField(max_length=255)
    netmask = models.IntegerField(default=64)
    created_date = models.DateTimeField(auto_now_add=True)
    domain_name = models.CharField(max_length=255, editable=False)
    domain_nameservers = models.ManyToManyField(Nameserver)
    domain_soa = models.CharField(max_length=255)
    domain_ttl = models.IntegerField(default=60)
    domain_serial = models.IntegerField(default=1)
    domain_active_serial = models.IntegerField(default=0, editable=False)
    domain_refresh = models.IntegerField(default=28800)
    domain_retry = models.IntegerField(default=7200)
    domain_expire = models.IntegerField(default=604800)
    domain_minimum_ttl = models.IntegerField(default=86400)
    domain_admin = models.EmailField()
    domain_filename = models.CharField(max_length=256)

    def __str__(self):
        return self.network + " (" + self.name + ")"

    @property
    def reverse_zone_name(self):
        """The ip6.arpa reverse zone name for this subnet's prefix.

        One label per nibble, derived from ``netmask`` (the prefix length).
        Delegation in ip6.arpa happens on nibble (4-bit) boundaries, so the
        prefix is truncated down to whole nibbles.
        """
        network = ipaddress.IPv6Address(f"{self.network}::")
        nibbles = self.netmask // 4
        return ".".join(network.exploded.replace(":", "")[:nibbles])[::-1] + ".ip6.arpa"

    def zone_file_contents(self, generate_unassigned=False):
        content = ""
        content += f"; zone file for {self.domain_name}\n"
        content += f"; {datetime.datetime.now()}\n"
        content += f"; filename: {self.domain_filename}\n"
        content += f"$TTL {self.domain_ttl}\n"
        content += "@ IN SOA {}. {}. (\n".format(
            self.domain_soa,
            self.domain_admin.replace("@", "."),
        )
        content += f"\t{self.domain_serial:d}\t; serial\n"
        content += f"\t{self.domain_refresh:d}\t; refresh\n"
        content += f"\t{self.domain_retry:d}\t; retry\n"
        content += f"\t{self.domain_expire:d}\t; expire\n"
        content += f"\t{self.domain_minimum_ttl:d} )\t; minimum ttl\n"
        content += ";\n"
        content += ";\n"

        for nameserver in self.domain_nameservers.all():
            content += f"@\tIN\tNS\t{nameserver.hostname}.\n"

        content += ";\n"

        # find the network
        # network = ipaddr.IPv6Address("%s::" % self.network)
        # content += "$ORIGIN " + ".".join(network.exploded.replace(":","")[:16])[::-1] + ".ip6.arpa.\n"

        for addr in self.ip6address_set.all():
            # if addr.interface_set.count() == 0: continue

            if addr.interface.domain is None:
                continue
            hostname = (
                f"{addr.interface.host.hostname}.{addr.interface.domain.domain_name}"
            )

            ip = ipaddress.IPv6Address(self.network + addr.address)
            ip = ".".join(ip.exploded.replace(":", "")[16:])[::-1]
            content += f"{ip}\tPTR\t{hostname}.\n"

            # addr = ipaddr.IPv6Address("%s%s" % (interface.
            # content += "%20s\tIN\tPTR\t%s.\n" % (addr.address.split(".")[3], hostname)

        return content

    class Meta:
        verbose_name = "IPv6 subnet"


class Ip4Subnet(models.Model):
    name = models.CharField(max_length=256)
    netmask = models.GenericIPAddressField(protocol="IPv4")
    network = models.GenericIPAddressField(protocol="IPv4")
    created_date = models.DateTimeField(auto_now_add=True)
    domain_name = models.CharField(max_length=255, editable=False)
    domain_nameservers = models.ManyToManyField(Nameserver)
    domain_soa = models.CharField(max_length=256)
    domain_ttl = models.IntegerField(default=60)
    domain_serial = models.IntegerField(default=1)
    domain_active_serial = models.IntegerField(default=0, editable=False)
    domain_refresh = models.IntegerField(default=28800)
    domain_retry = models.IntegerField(default=7200)
    domain_expire = models.IntegerField(default=604800)
    domain_minimum_ttl = models.IntegerField(default=86400)
    domain_admin = models.EmailField()
    domain_filename = models.CharField(max_length=256)

    dhcp_dynamic = models.BooleanField(default=False)
    dhcp_dynamic_start = models.GenericIPAddressField(
        protocol="IPv4", null=True, blank=True
    )
    dhcp_dynamic_end = models.GenericIPAddressField(
        protocol="IPv4", null=True, blank=True
    )
    dhcp_config = models.ForeignKey(DhcpConfig, models.CASCADE)

    def __str__(self):
        return self.network + " (" + self.name + ")"

    @property
    def reverse_zone_name(self):
        """The in-addr.arpa reverse zone name for this subnet.

        Masks of /24 or shorter give the standard octet-boundary name
        (190.36.158.in-addr.arpa).  Masks longer than /24 give the RFC 2317
        classless name for the sub-/24 block (192-26.190.36.158.in-addr.arpa).
        This is the apex BIND expects -- it must match the zone name in
        named.conf or rndc refuses to load the file.
        """
        net = ipaddress.IPv4Network(f"{self.network}/{self.netmask}", strict=False)
        o1, o2, o3, o4 = str(net.network_address).split(".")
        rev = f"{o3}.{o2}.{o1}"
        if net.prefixlen > 24:
            return f"{o4}-{net.prefixlen:d}.{rev}.in-addr.arpa"
        return f"{rev}.in-addr.arpa"

    def zone_file_contents(self, generate_unassigned=False):
        content = ""
        content += f"; zone file for {self.domain_name}\n"
        content += f"; {datetime.datetime.now()}\n"
        content += f"; filename: {self.domain_filename}\n"
        content += f"$TTL {self.domain_ttl}\n"
        content += "@ IN SOA {}. {}. (\n".format(
            self.domain_soa,
            self.domain_admin.replace("@", "."),
        )
        content += f"\t{self.domain_serial:d}\t; serial\n"
        content += f"\t{self.domain_refresh:d}\t; refresh\n"
        content += f"\t{self.domain_retry:d}\t; retry\n"
        content += f"\t{self.domain_expire:d}\t; expire\n"
        content += f"\t{self.domain_minimum_ttl:d} )\t; minimum ttl\n"
        content += ";\n"
        content += ";\n"

        for nameserver in self.domain_nameservers.all():
            content += f"@\tIN\tNS\t{nameserver.hostname}.\n"

        content += ";\n"

        for addr in self.ip4address_set.all():
            """ Get PTR records for each v4 address in subnet """
            if hasattr(addr, "interface") and addr.interface.domain:
                hostname = f"{addr.interface.host.hostname}.{addr.interface.domain.domain_name}"
                content += f"{addr.address.split('.')[3]:<20}\tIN\tPTR\t{hostname}.\n"
            elif not hasattr(addr, "interface") and generate_unassigned:
                content += "{}\tIN\tPTR\t{}.{}\n".format(
                    addr.address,
                    addr.address.split(".")[3],
                    "dhcp.neuf.no.",
                )

        return content

    class Meta:
        verbose_name = "IPv4 subnet"


class DhcpOption(models.Model):
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    ip4subnet = models.ForeignKey(Ip4Subnet, models.CASCADE)

    def __str__(self):
        return self.key + " " + self.value

    class Meta:
        verbose_name = "DHCP option"


class DhcpCustomField(models.Model):
    value = models.CharField(max_length=255)
    ip4subnet = models.ForeignKey(Ip4Subnet, models.CASCADE)

    class Meta:
        verbose_name = "DHCP custom field"


class Ip4Address(models.Model):
    subnet = models.ForeignKey(Ip4Subnet, models.CASCADE)
    address = models.GenericIPAddressField(protocol="IPv4")
    last_contact = models.DateTimeField(null=True, blank=True)
    ping_avg_rtt = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.address

    class Meta:
        verbose_name = "IPv4 address"
        verbose_name_plural = "IPv4 addresses"


class HostType(models.Model):
    host_type = models.CharField(max_length=64)
    description = models.CharField(max_length=1024)

    def __str__(self):
        return self.host_type

    def num_members(self):
        return self.host_set.count()

    class Meta:
        ordering = ("host_type",)


class OperatingSystem(models.Model):
    OS_ARCHITECTURES = (
        ("mips", _("MIPS")),
        ("arm", _("ARM")),
        ("broadcom", _("Broadcom")),
        ("rc32300", _("RC32300")),
        ("powerpc", _("PowerPC")),
        ("powerpc403ga", _("PowerPC403GA")),
        ("unknown", _("Unknown")),
        ("x86_64", _("x86-64")),
        ("i386", _("x86")),
    )
    name = models.CharField(max_length=256)
    version = models.CharField(max_length=64)
    arch = models.CharField(
        max_length=255, choices=OS_ARCHITECTURES, blank=True, null=True
    )

    def __str__(self):
        return self.name + " " + self.version + " (" + self.arch + ")"

    class Meta:
        ordering = ("name", "version")


class Host(models.Model):
    location = models.CharField(max_length=1024)
    brand = models.CharField(max_length=1024)
    model = models.CharField(max_length=1024)
    owner = models.CharField(max_length=1024)
    hostname = models.CharField(max_length=64, validators=[validate_hostname])
    serial_number = models.CharField(max_length=256)
    description = models.CharField(max_length=1024)
    created_date = models.DateTimeField(auto_now_add=True)
    host_type = models.ForeignKey(HostType, models.CASCADE)  # FIXME: SET_NULL?
    virtual = models.BooleanField(default=False)
    allow_email = models.BooleanField(default=False)
    operating_system = models.ForeignKey(
        OperatingSystem, models.CASCADE
    )  # FIXME: SET_NULL?

    request_kerberos_principal = models.BooleanField(default=False)
    kerberos_principal_created = models.BooleanField(default=False, editable=False)
    kerberos_principal_name = models.CharField(max_length=256, editable=False)
    kerberos_principal_created_date = models.DateTimeField(
        null=True, blank=True, editable=False
    )

    pxe_key = models.CharField(max_length=254, blank=True)
    pxe_installable = models.BooleanField(default=False)

    def __str__(self):
        return self.hostname


class Interface(models.Model):
    name = models.CharField(max_length=128)
    macaddr = models.CharField(max_length=17, validators=[validate_macaddr])
    pxe_filename = models.CharField(max_length=64, blank=True)
    dhcp_client = models.BooleanField(default=False)
    host = models.ForeignKey(Host, models.CASCADE)
    ip4address = models.OneToOneField(
        Ip4Address, blank=True, null=True, on_delete=models.SET_NULL
    )
    created_date = models.DateTimeField(auto_now_add=True)
    domain = models.ForeignKey(Domain, models.CASCADE)

    def __str__(self):
        return f"{self.macaddr} ({self.name} on {self.host.hostname})"

    def ipv6_enabled(self):
        return self.ip6address_set.exists()


class Ip6Address(models.Model):
    subnet = models.ForeignKey(Ip6Subnet, models.CASCADE)
    address = models.GenericIPAddressField(protocol="IPv6")
    interface = models.ForeignKey(Interface, models.CASCADE)

    def full_address(self):
        return self.subnet.network + self.address

    def __str__(self):
        return f"{self.full_address()} ({self.interface.name} on {self.interface.host.hostname})"

    class Meta:
        verbose_name = "IPv6 address"
        verbose_name_plural = "IPv6 addresses"
