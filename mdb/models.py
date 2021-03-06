from django.db import models
from django.utils.translation import ugettext_lazy as _
from mdb.pxe import host_as_pxe_files

from mdb.validators import validate_hostname, validate_macaddr

import ipaddress
import datetime


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
    domain_ipaddr = models.GenericIPAddressField(protocol='IPv4')
    domain_ip6addr = models.GenericIPAddressField(protocol='IPv6', blank=True, null=True)
    domain_filename = models.CharField(max_length=256)
    created_date = models.DateTimeField(auto_now_add=True)

    domain_nameservers = models.ManyToManyField(Nameserver)
    domain_mailexchanges = models.ManyToManyField(MailExchange)

    def __str__(self):
        return self.domain_name

    def __eq__(self, other):
        if not other or not hasattr(other, 'domain_name'):
            return False

        return self.domain_name == other.domain_name

    def zone_file_contents(self):
        content = "; serial:%d\n" % self.domain_serial
        content += "; zone file for %s\n" % self.domain_name
        content += "; %s\n" % datetime.datetime.now()
        content += "; filename: %s\n" % self.domain_filename
        content += "$TTL %s\n" % self.domain_ttl
        content += "@ IN SOA %s. %s. (\n" % (
            self.domain_soa,
            self.domain_admin.replace("@", "."))
        content += "\t%d\t; serial\n" % self.domain_serial
        content += "\t%d\t; refresh\n" % self.domain_refresh
        content += "\t%d\t; retry\n" % self.domain_retry
        content += "\t%d\t; expire\n" % self.domain_expire
        content += "\t%d )\t; minimum ttl\n" % self.domain_minimum_ttl
        content += ";\n"

        for nameserver in self.domain_nameservers.all():
            content += "@\tIN\tNS\t%s.\n" % nameserver.hostname

        for mx in self.domain_mailexchanges.all():
            content += "@\t\tMX\t%d %s.\n" % (mx.priority, mx.hostname)

        if self.domain_ipaddr is not None:
            content += "@\tIN\tA\t%s\n" % self.domain_ipaddr

        if self.domain_ip6addr:
            content += "@\tIN\tAAAA\t%s\n" % self.domain_ip6addr

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
            content += "%s\tIN\tCNAME\t%s\n" % (cname.name, cname.target)

        content += "; TXT records \n"

        for txt in self.domaintxtrecord_set.all():
            content += txt.as_record() + "\n"

        content += "; HOST records\n"

        for interface in self.interface_set.all():
            host = interface.host
            if interface.ip4address:
                content += "%-20s\tIN\tA\t%s\n" % (
                    host.hostname,
                    interface.ip4address.address)
            for ipv6addr in interface.ip6address_set.all():
                content += "%-20s\tIN\tAAAA\t%s\n" % (
                    host.hostname,
                    ipv6addr.full_address())

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
        return '{}.{}.{}. IN SRV {} {} {} {}.'.format(
            self.srvce,
            self.prot,
            self.name,

            self.priority,
            self.weight,
            self.port,
            self.target
        )

    def __str__(self):
        return self.as_record()


class DomainTxtRecord(models.Model):
    name = models.CharField(max_length=256)
    target = models.CharField(max_length=256)
    domain = models.ForeignKey(Domain, models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)

    def as_record(self):
        return '{} TXT {}'.format(self.name, self.target)

    def __str__(self):
        return self.as_record()


class DomainCnameRecord(models.Model):
    name = models.CharField(max_length=256)
    target = models.CharField(max_length=256)
    domain = models.ForeignKey(Domain, models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)

    def as_record(self):
        return '{} IN CNAME {}'.format(self.name, self.target)

    def __str__(self):
        return self.as_record()


class DomainARecord(models.Model):
    name = models.CharField(max_length=256)
    target = models.GenericIPAddressField(protocol='IPv4')
    domain = models.ForeignKey(Domain, models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)

    def as_record(self):
        return '{} IN A {}'.format(self.name, self.target)

    def __str__(self):
        return self.as_record()


class DomainAAAARecord(models.Model):
    name = models.CharField(max_length=256)
    target = models.GenericIPAddressField(protocol='IPv6')
    domain = models.ForeignKey(Domain, models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)

    def as_record(self):
        return '{} IN AAAA {}'.format(self.name, self.target)

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
        content = "# Autogenerated configuration %s\n" % datetime.datetime.now()
        if self.authoritative:
            content += "authoritative;\n"
        content += "default-lease-time %d;\n" % self.default_lease_time
        content += "max-lease-time %d;\n" % self.max_lease_time
        content += "log-facility %s;\n" % self.log_facility
        content += "ddns-update-style %s;\n" % self.ddns_update_style

        # time to write the subnet definitions
        for subnet in self.ip4subnet_set.all():
            content += "\n# %s\n" % subnet.name
            content += "subnet %s netmask %s {\n" % (
                subnet.network,
                subnet.netmask)

            for option in subnet.dhcpoption_set.all():
                content += "\toption %s %s;\n" % (option.key, option.value)

            for option in subnet.dhcpcustomfield_set.all():
                content += "\t%s;\n" % option.value

            if subnet.dhcp_dynamic:
                content += "\trange %s %s;\n" \
                    % (subnet.dhcp_dynamic_start, subnet.dhcp_dynamic_end)

            content += "}\n"

        # time to write host definitions
        for subnet in self.ip4subnet_set.all():
            for ip4address in subnet.ip4address_set.all():
                if not hasattr(ip4address, 'interface') or not ip4address.interface.dhcp_client:
                    continue
                _if = ip4address.interface
                content += "\nhost %s {\n" % _if.host.hostname
                content += "\thardware ethernet %s;\n" % _if.macaddr
                content += "\tfixed-address %s.%s;\n" % \
                    (_if.host.hostname, _if.domain.domain_name)
                if len(_if.pxe_filename) > 0:
                    content += "\tfilename \"%s\";\n" % _if.pxe_filename
                content += "}\n"

        return content

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'DHCP config'


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

    def zone_file_contents(self, generate_unassigned=False):
        content = ""
        content += "; zone file for %s\n" % self.domain_name
        content += "; %s\n" % datetime.datetime.now()
        content += "; filename: %s\n" % self.domain_filename
        content += "$TTL %s\n" % self.domain_ttl
        content += "@ IN SOA %s. %s. (\n" % (
            self.domain_soa,
            self.domain_admin.replace("@", "."))
        content += "\t%d\t; serial\n" % self.domain_serial
        content += "\t%d\t; refresh\n" % self.domain_refresh
        content += "\t%d\t; retry\n" % self.domain_retry
        content += "\t%d\t; expire\n" % self.domain_expire
        content += "\t%d )\t; minimum ttl\n" % self.domain_minimum_ttl
        content += ";\n"
        content += ";\n"

        for nameserver in self.domain_nameservers.all():
            content += "@\tIN\tNS\t%s.\n" % nameserver.hostname

        content += ";\n"

        # find the network
        # network = ipaddr.IPv6Address("%s::" % self.network)
        # content += "$ORIGIN " + ".".join(network.exploded.replace(":","")[:16])[::-1] + ".ip6.arpa.\n"

        for addr in self.ip6address_set.all():
            # if addr.interface_set.count() == 0: continue

            if addr.interface.domain is None:
                continue
            hostname = "%s.%s" % (
                addr.interface.host.hostname,
                addr.interface.domain.domain_name)

            ip = ipaddress.IPv6Address(self.network + addr.address)
            ip = ".".join(ip.exploded.replace(":", "")[16:])[::-1]
            content += "%s\tPTR\t%s.\n" % (ip, hostname)

            # addr = ipaddr.IPv6Address("%s%s" % (interface.
            # content += "%20s\tIN\tPTR\t%s.\n" % (addr.address.split(".")[3], hostname)

        return content

    class Meta:
        verbose_name = 'IPv6 subnet'


class Ip4Subnet(models.Model):
    name = models.CharField(max_length=256)
    netmask = models.GenericIPAddressField(protocol='IPv4')
    network = models.GenericIPAddressField(protocol='IPv4')
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
    dhcp_dynamic_start = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    dhcp_dynamic_end = models.GenericIPAddressField(protocol='IPv4', null=True, blank=True)
    dhcp_config = models.ForeignKey(DhcpConfig, models.CASCADE)

    def __str__(self):
        return self.network + " (" + self.name + ")"

    def zone_file_contents(self, generate_unassigned=False):
        content = ""
        content += "; zone file for %s\n" % self.domain_name
        content += "; %s\n" % datetime.datetime.now()
        content += "; filename: %s\n" % self.domain_filename
        content += "$TTL %s\n" % self.domain_ttl
        content += "@ IN SOA %s. %s. (\n" % (
            self.domain_soa,
            self.domain_admin.replace("@", "."))
        content += "\t%d\t; serial\n" % self.domain_serial
        content += "\t%d\t; refresh\n" % self.domain_refresh
        content += "\t%d\t; retry\n" % self.domain_retry
        content += "\t%d\t; expire\n" % self.domain_expire
        content += "\t%d )\t; minimum ttl\n" % self.domain_minimum_ttl
        content += ";\n"
        content += ";\n"

        for nameserver in self.domain_nameservers.all():
            content += "@\tIN\tNS\t%s.\n" % nameserver.hostname

        content += ";\n"

        for addr in self.ip4address_set.all():
            """ Get PTR records for each v4 address in subnet """
            if hasattr(addr, 'interface') and addr.interface.domain:
                hostname = "%s.%s" % (
                    addr.interface.host.hostname,
                    addr.interface.domain.domain_name)
                content += "%-20s\tIN\tPTR\t%s.\n" % \
                    (addr.address.split(".")[3], hostname)
            elif not hasattr(addr, 'interface') and generate_unassigned:
                content += "%s\tIN\tPTR\t%s.%s\n" % (
                    addr.address,
                    addr.address.split(".")[3],
                    "dhcp.neuf.no.")

        return content

    class Meta:
        verbose_name = 'IPv4 subnet'


class DhcpOption(models.Model):
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    ip4subnet = models.ForeignKey(Ip4Subnet, models.CASCADE)

    def __str__(self):
        return self.key + " " + self.value

    class Meta:
        verbose_name = 'DHCP option'


class DhcpCustomField(models.Model):
    value = models.CharField(max_length=255)
    ip4subnet = models.ForeignKey(Ip4Subnet, models.CASCADE)

    class Meta:
        verbose_name = 'DHCP custom field'


class Ip4Address(models.Model):
    subnet = models.ForeignKey(Ip4Subnet, models.CASCADE)
    address = models.GenericIPAddressField(protocol='IPv4')
    last_contact = models.DateTimeField(null=True, blank=True)
    ping_avg_rtt = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.address

    class Meta:
        verbose_name = 'IPv4 address'
        verbose_name_plural = 'IPv4 addresses'


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
        ('mips', _('MIPS')),
        ('arm', _('ARM')),
        ('broadcom', _('Broadcom')),
        ('rc32300', _('RC32300')),
        ('powerpc', _('PowerPC')),
        ('powerpc403ga', _('PowerPC403GA')),
        ('unknown', _('Unknown')),
        ('x86_64', _('x86-64')),
        ('i386', _('x86')),
    )
    name = models.CharField(max_length=256)
    version = models.CharField(max_length=64)
    arch = models.CharField(max_length=255, choices=OS_ARCHITECTURES, blank=True, null=True)

    pxe_kernel = models.CharField(max_length=255, blank=True, null=True)
    pxe_initrd = models.CharField(max_length=255, blank=True, null=True)
    pxe_preseed_config_url = models.URLField(blank=True, null=True)

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
    operating_system = models.ForeignKey(OperatingSystem, models.CASCADE)  # FIXME: SET_NULL?

    request_kerberos_principal = models.BooleanField(default=False)
    kerberos_principal_created = models.BooleanField(default=False, editable=False)
    kerberos_principal_name = models.CharField(max_length=256, editable=False)
    kerberos_principal_created_date = models.DateTimeField(null=True, blank=True, editable=False)

    pxe_key = models.CharField(max_length=254, blank=True)
    pxe_installable = models.BooleanField(default=False)

    def __str__(self):
        return self.hostname

    def as_pxe_files(self):
        return host_as_pxe_files(self)


class Interface(models.Model):
    name = models.CharField(max_length=128)
    macaddr = models.CharField(max_length=17, validators=[validate_macaddr])
    pxe_filename = models.CharField(max_length=64, blank=True)
    dhcp_client = models.BooleanField(default=False)
    host = models.ForeignKey(Host, models.CASCADE)
    ip4address = models.OneToOneField(Ip4Address, blank=True, null=True, on_delete=models.SET_NULL)
    created_date = models.DateTimeField(auto_now_add=True)
    domain = models.ForeignKey(Domain, models.CASCADE)

    def __str__(self):
        return "%s (%s on %s)" % (self.macaddr, self.name, self.host.hostname)

    def ipv6_enabled(self):
        return self.ip6address_set.exists()


class Ip6Address(models.Model):
    subnet = models.ForeignKey(Ip6Subnet, models.CASCADE)
    address = models.GenericIPAddressField(protocol='IPv6')
    interface = models.ForeignKey(Interface, models.CASCADE)

    def full_address(self):
        return self.subnet.network + self.address

    def __str__(self):
        return "%s (%s on %s)" % (
            self.full_address(),
            self.interface.name,
            self.interface.host.hostname)

    class Meta:
        verbose_name = 'IPv6 address'
        verbose_name_plural = 'IPv6 addresses'
