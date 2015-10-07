from django.contrib import admin, messages

from mdb.models import Ip6Address, Interface, Ip4Address, DhcpOption, DhcpCustomField, DomainSrvRecord, DomainTxtRecord, \
    DomainCnameRecord, DomainARecord, Domain, Host, Ip4Subnet, Ip6Subnet, Nameserver, MailExchange, OperatingSystem, \
    HostType, DhcpConfig


class Ip6AddressInline(admin.TabularInline):
    model = Ip6Address
    extra = 0


class InterfaceInline(admin.TabularInline):
    inlines = [Ip6AddressInline]
    model = Interface
    extra = 0

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
            'fields': (('hostname', 'host_type'), ('pxe_key', 'pxe_installable'), ('brand', 'model'), 'serial_number', ('operating_system', 'virtual'))
        }),
        # FIXME: Not in use
        # ('Domain and Kerberos Information', {
        #     'description': 'If this host is a member of the LDAP domain, you need to tick the request kerberos principal checkbox. A principal will then be created for the host.',
        #     'classes': ['collapse'],
        #     'fields': ('request_kerberos_principal', 'kerberos_principal_created',
        #                ('kerberos_principal_name', 'kerberos_principal_created_date'))
        # }),
    )
    actions = ['set_installable']

    def _get_host_warning_message(self, host, ifs):
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


class DhcpOptionInline(admin.TabularInline):
    model = DhcpOption
    extra = 0


class DhcpCustomFieldInline(admin.TabularInline):
    model = DhcpCustomField
    extra = 0


class SubnetAdmin(admin.ModelAdmin):
    list_display = ['name', 'network', 'netmask', 'num_addresses', 'broadcast_address', 'first_address', 'last_address']
    inlines = [DhcpOptionInline, DhcpCustomFieldInline, Ip4AddressInline]

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


class DomainAdmin(admin.ModelAdmin):
    inlines = [DomainSrvRecordInline, DomainTxtRecordInline, DomainARecordInline, DomainCnameRecordInline]
    list_display = ['domain_name', 'domain_soa', 'domain_admin', 'num_records', 'domain_ipaddr']
    search_fields = ['domain_name']


class HostTypeAdmin(admin.ModelAdmin):
    list_display = ['host_type', 'description', 'num_members']


class OperatingSystemAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'arch']


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
