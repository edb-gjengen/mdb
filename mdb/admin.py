import ipaddress
from django.conf import settings

from django.contrib import admin, messages
from django.db.models import Count
from mdb.forms import InterfaceForm
from mdb.models import (
    Ip6Address, Interface, Ip4Address, DhcpOption, DhcpCustomField, DomainSrvRecord, DomainTxtRecord,
    DomainCnameRecord, DomainARecord, Domain, Host, Ip4Subnet, Ip6Subnet, Nameserver, MailExchange, OperatingSystem,
    HostType, DhcpConfig, DomainAAAARecord)


admin.site.site_header = settings.ADMIN_SITE_NAME


class Ip6AddressInline(admin.TabularInline):
    model = Ip6Address
    extra = 0


class InterfaceInline(admin.TabularInline):
    inlines = [Ip6AddressInline]
    model = Interface
    extra = 0
    form = InterfaceForm

    def get_queryset(self, request):
        return super(InterfaceInline, self).get_queryset(request).select_related()


class HostAdmin(admin.ModelAdmin):
    ordering = ('hostname',)
    inlines = [InterfaceInline]
    list_display = ['hostname', 'owner', 'host_type', 'location', 'mac_addresses', 'ip_addresses', 'in_domain',
                    'pxe_installable', 'ipv6_enabled']
    list_filter = ['host_type', 'owner', 'location', 'pxe_installable']
    readonly_fields = ['kerberos_principal_name', 'kerberos_principal_created_date',
                       'kerberos_principal_created']
    search_fields = ['hostname', 'location', 'interface__macaddr', 'interface__ip4address__address']
    fieldsets = (
        ('Owner Information', {
            'fields': ('owner', 'location', 'description')
        }),
        ('Hardware and Software Information', {
            'fields': (
                ('hostname', 'host_type'),
                ('pxe_key', 'pxe_installable'),
                ('brand', 'model'),
                'serial_number',
                ('operating_system', 'virtual'))
        }),
    )
    actions = ['set_installable']

    def mac_addresses(self, host):
        addresses = host.interface_set.filter(macaddr__isnull=False).values_list('macaddr', flat=True)
        return ", ".join(addresses)

    def ip_addresses(self, host):
        addresses = host.interface_set.filter(ip4address__isnull=False).values_list('ip4address__address', flat=True)
        return ", ".join(addresses)

    def in_domain(self, host):
        domains = host.interface_set.values_list('domain__domain_name', flat=True)
        return ",".join(domains)

    in_domain.short_description = "in domains"

    def ipv6_enabled(self, host):
        ipv6_ifs = host.interface_set.annotate(num_ipv6=Count('ip6address')).filter(num_ipv6__gt=0)
        return ipv6_ifs.exists()

    ipv6_enabled.boolean = True
    # FIXME: custom filter to sort custom field

    @staticmethod
    def _get_host_warning_message(host, ifs):
        ifs_str = ', '.join([_if.name for _if in ifs])
        return 'Host {} might not be installable since interface(s) {} has no IP set.'.format(host, ifs_str)

    def set_installable(self, request, queryset):
        invalid_ifs_per_host = []

        for obj in queryset:
            invalid_ifs = obj.interface_set.filter(ip4address__isnull=True)
            if invalid_ifs.exists():
                invalid_ifs_per_host.append(self._get_host_warning_message(obj, invalid_ifs))
            obj.pxe_installable = True
            obj.save()  # triggers post save signal

        if invalid_ifs_per_host:
            self.message_user(request, message='\n'.join(invalid_ifs_per_host), level=messages.WARNING)

    set_installable.short_description = "Mark selected hosts as PXE installable"

    def get_queryset(self, request):
        return super(HostAdmin, self).get_queryset(request).select_related()


class Ip4AddressInline(admin.TabularInline):
    model = Ip4Address
    extra = 0
    readonly_fields = ['address', 'assigned_to_host']

    def assigned_to_host(self, addr):
        return addr.interface.host

    assigned_to_host.short_description = "Assigned to Host"


class DhcpOptionInline(admin.TabularInline):
    model = DhcpOption
    extra = 0


class DhcpCustomFieldInline(admin.TabularInline):
    model = DhcpCustomField
    extra = 0


class SubnetAdmin(admin.ModelAdmin):
    list_display = ['name', 'network', 'netmask', 'num_addresses', 'broadcast_address', 'first_address', 'last_address']
    inlines = [DhcpOptionInline, DhcpCustomFieldInline, Ip4AddressInline]

    def num_addresses(self, ip4subnet):
        subnet = ipaddress.IPv4Network(ip4subnet.network + "/" + ip4subnet.netmask)
        return subnet.num_addresses

    def broadcast_address(self, ip4subnet):
        subnet = ipaddress.IPv4Network(ip4subnet.network + "/" + ip4subnet.netmask)
        return subnet.broadcast_address

    def first_address(self, ip4subnet):
        subnet = ipaddress.IPv4Network(ip4subnet.network + "/" + ip4subnet.netmask)
        return next(subnet.hosts())

    def last_address(self, ip4subnet):
        subnet = ipaddress.IPv4Network(ip4subnet.network + "/" + ip4subnet.netmask)
        return list(subnet.hosts())[-1]

    broadcast_address.short_description = 'broadcast'
    num_addresses.short_description = '#addresses'
    first_address.short_description = 'first address'
    last_address.short_description = 'last address'

    def get_queryset(self, request):
        # TODO: optimize
        return super(SubnetAdmin, self).get_queryset(request)


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


class DomainAdmin(admin.ModelAdmin):
    inlines = [DomainSrvRecordInline, DomainTxtRecordInline, DomainARecordInline, DomainAAAARecordInline,
               DomainCnameRecordInline]
    list_display = ['domain_name', 'domain_soa', 'domain_admin', 'num_records', 'domain_ipaddr',  'domain_ip6addr']
    search_fields = ['domain_name']

    def num_records(self, domain):
        host_a_records = Host.objects.filter(interface__domain=domain).count()
        size = {
            "CNAME": domain.domaincnamerecord_set.count(),
            "SRV": domain.domainsrvrecord_set.count(),
            "TXT": domain.domaintxtrecord_set.count(),
            "A": domain.domainarecord_set.count() + host_a_records
        }
        return ', '.join(['{}: {}'.format(k, v) for k, v in size.items()])

    num_records.short_description = "Num Records"


class HostTypeAdmin(admin.ModelAdmin):
    list_display = ['host_type', 'description', 'num_members']


class OperatingSystemAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'arch', 'pxe_kernel', 'pxe_initrd', 'pxe_preseed_config_url']


admin.site.register(Domain, DomainAdmin)
admin.site.register(Host, HostAdmin)
admin.site.register(Ip4Subnet, SubnetAdmin)
admin.site.register(Ip6Subnet)
admin.site.register(Ip6Address)
admin.site.register(Nameserver)
admin.site.register(MailExchange)
admin.site.register(OperatingSystem, OperatingSystemAdmin)
admin.site.register(HostType, HostTypeAdmin)
admin.site.register(DhcpConfig)
admin.site.register(DhcpOption)
