import ipaddress

from django.conf import settings
from django.contrib import admin, messages
from django.db import models
from django.db.models import Count
from django.forms import NumberInput

from mdb.forms import InterfaceForm, SerialNumberInput
from mdb.models import (
    DhcpConfig,
    DhcpCustomField,
    DhcpOption,
    Domain,
    DomainAAAARecord,
    DomainARecord,
    DomainCnameRecord,
    DomainSrvRecord,
    DomainTxtRecord,
    Host,
    HostType,
    Interface,
    Ip4Address,
    Ip4Subnet,
    Ip6Address,
    Ip6Subnet,
    MailExchange,
    Nameserver,
    OperatingSystem,
)

admin.site.site_header = settings.ADMIN_SITE_NAME


class SerialFieldAdminMixin:
    """Render the ``domain_serial`` field with the wide serial widget + button."""

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "domain_serial":
            formfield.widget = SerialNumberInput()
        return formfield


class Ip6AddressInline(admin.TabularInline):
    model = Ip6Address
    extra = 0


class InterfaceInline(admin.TabularInline):
    inlines = [Ip6AddressInline]
    model = Interface
    extra = 0
    form = InterfaceForm

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("host", "domain")


@admin.register(Host)
class HostAdmin(admin.ModelAdmin):
    ordering = ("hostname",)
    inlines = [InterfaceInline]
    list_display = [
        "hostname",
        "owner",
        "host_type",
        "location",
        "mac_addresses",
        "ip_addresses",
        "in_domain",
        "pxe_installable",
        "ipv6_enabled",
        "allow_email",
    ]
    list_filter = ["host_type", "owner", "location", "pxe_installable", "allow_email"]
    readonly_fields = [
        "kerberos_principal_name",
        "kerberos_principal_created_date",
        "kerberos_principal_created",
    ]
    search_fields = [
        "hostname",
        "location",
        "interface__macaddr",
        "interface__ip4address__address",
    ]
    fieldsets = (
        ("Owner Information", {"fields": ("owner", "location", "description")}),
        (
            "Hardware and Software Information",
            {
                "fields": (
                    ("hostname", "host_type"),
                    ("pxe_key", "pxe_installable"),
                    ("brand", "model"),
                    "serial_number",
                    ("operating_system", "virtual"),
                    "allow_email",
                )
            },
        ),
    )
    actions = ["set_installable"]

    def mac_addresses(self, host):
        addresses = host.interface_set.filter(macaddr__isnull=False).values_list(
            "macaddr", flat=True
        )
        return ", ".join(addresses)

    def ip_addresses(self, host):
        addresses = host.interface_set.filter(ip4address__isnull=False).values_list(
            "ip4address__address", flat=True
        )
        return ", ".join(addresses)

    @admin.display(description="in domains")
    def in_domain(self, host):
        domains = host.interface_set.values_list("domain__domain_name", flat=True)
        return ",".join(domains)

    @admin.display(boolean=True)
    def ipv6_enabled(self, host):
        ipv6_ifs = host.interface_set.annotate(num_ipv6=Count("ip6address")).filter(
            num_ipv6__gt=0
        )
        return ipv6_ifs.exists()

    # FIXME: custom filter to sort custom field

    @staticmethod
    def _get_host_warning_message(host, ifs):
        ifs_str = ", ".join([_if.name for _if in ifs])
        return f"Host {host} might not be installable since interface(s) {ifs_str} has no IP set."

    @admin.action(description="Mark selected hosts as PXE installable")
    def set_installable(self, request, queryset):
        invalid_ifs_per_host = []

        for obj in queryset:
            invalid_ifs = obj.interface_set.filter(ip4address__isnull=True)
            if invalid_ifs.exists():
                invalid_ifs_per_host.append(
                    self._get_host_warning_message(obj, invalid_ifs)
                )
            obj.pxe_installable = True
            obj.save()  # triggers post save signal

        if invalid_ifs_per_host:
            self.message_user(
                request, message="\n".join(invalid_ifs_per_host), level=messages.WARNING
            )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("host_type", "operating_system")
        )


class Ip4AddressInline(admin.TabularInline):
    model = Ip4Address
    extra = 0
    readonly_fields = ["address", "assigned_to_host"]

    @admin.display(description="Assigned to Host")
    def assigned_to_host(self, addr):
        return addr.interface.host


class DhcpOptionInline(admin.TabularInline):
    model = DhcpOption
    extra = 0


class DhcpCustomFieldInline(admin.TabularInline):
    model = DhcpCustomField
    extra = 0


@admin.register(Ip4Subnet)
class Ip4SubnetAdmin(SerialFieldAdminMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "network",
        "netmask",
        "domain_name",
        "num_addresses",
        "broadcast_address",
        "first_address",
        "last_address",
    ]
    readonly_fields = ["domain_name"]
    inlines = [DhcpOptionInline, DhcpCustomFieldInline, Ip4AddressInline]

    @admin.display(description="# addresses")
    def num_addresses(self, ip4subnet):
        subnet = ipaddress.IPv4Network(ip4subnet.network + "/" + ip4subnet.netmask)
        return subnet.num_addresses

    @admin.display(description="broadcast")
    def broadcast_address(self, ip4subnet):
        subnet = ipaddress.IPv4Network(ip4subnet.network + "/" + ip4subnet.netmask)
        return subnet.broadcast_address

    @admin.display(description="first address")
    def first_address(self, ip4subnet):
        subnet = ipaddress.IPv4Network(ip4subnet.network + "/" + ip4subnet.netmask)
        return next(subnet.hosts())

    @admin.display(description="last address")
    def last_address(self, ip4subnet):
        subnet = ipaddress.IPv4Network(ip4subnet.network + "/" + ip4subnet.netmask)
        return list(subnet.hosts())[-1]

    def get_queryset(self, request):
        # TODO: optimize
        return super().get_queryset(request)


@admin.register(Ip6Subnet)
class Ip6SubnetAdmin(SerialFieldAdminMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "network",
        "netmask",
        "domain_name",
        "num_addresses",
        "first_address",
        "last_address",
    ]
    readonly_fields = ["domain_name"]

    def _network(self, ip6subnet):
        return ipaddress.IPv6Network(
            f"{ip6subnet.network}::/{ip6subnet.netmask:d}", strict=False
        )

    @admin.display(description="# addresses")
    def num_addresses(self, ip6subnet):
        return self._network(ip6subnet).num_addresses

    @admin.display(description="first address")
    def first_address(self, ip6subnet):
        return self._network(ip6subnet).network_address

    @admin.display(description="last address")
    def last_address(self, ip6subnet):
        # subnet[-1] is O(1); never materialize hosts() for a /64.
        return self._network(ip6subnet)[-1]


class DomainSrvRecordInline(admin.TabularInline):
    model = DomainSrvRecord
    extra = 0


class DomainTxtRecordInline(admin.TabularInline):
    model = DomainTxtRecord
    extra = 0


class DomainCnameRecordInline(admin.TabularInline):
    model = DomainCnameRecord
    extra = 0


class DomainARecordInline(admin.TabularInline):
    model = DomainARecord
    extra = 0


class DomainAAAARecordInline(admin.TabularInline):
    model = DomainAAAARecord
    extra = 0


@admin.register(Domain)
class DomainAdmin(SerialFieldAdminMixin, admin.ModelAdmin):
    inlines = [
        DomainSrvRecordInline,
        DomainTxtRecordInline,
        DomainARecordInline,
        DomainAAAARecordInline,
        DomainCnameRecordInline,
    ]
    list_display = [
        "domain_name",
        "domain_soa",
        "domain_admin",
        "num_records",
        "domain_ipaddr",
        "domain_ip6addr",
    ]
    search_fields = ["domain_name"]
    formfield_overrides = {
        models.IntegerField: {"widget": NumberInput(attrs={"style": "width: 10em"})},
    }

    @admin.display(description="Num Records")
    def num_records(self, domain):
        host_a_records = Host.objects.filter(interface__domain=domain).count()
        size = {
            "CNAME": domain.domaincnamerecord_set.count(),
            "SRV": domain.domainsrvrecord_set.count(),
            "TXT": domain.domaintxtrecord_set.count(),
            "A": domain.domainarecord_set.count() + host_a_records,
        }
        return ", ".join([f"{k}: {v}" for k, v in size.items()])


@admin.register(HostType)
class HostTypeAdmin(admin.ModelAdmin):
    list_display = ["host_type", "description", "num_members"]


@admin.register(OperatingSystem)
class OperatingSystemAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "version",
        "arch",
        "pxe_kernel",
        "pxe_initrd",
        "pxe_preseed_config_url",
    ]


admin.site.register(Ip6Address)
admin.site.register(Nameserver)
admin.site.register(MailExchange)
admin.site.register(DhcpConfig)
admin.site.register(DhcpOption)
