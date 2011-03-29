from mdb.models import *
from django.contrib import admin

class InterfaceInline(admin.TabularInline):
	model = Interface
	extra = 0

class HostAdmin(admin.ModelAdmin):
	inlines = [InterfaceInline]
	list_display = ['hostname', 'brand', 'owner', 'host_type', 'location', 'serial_number', 'in_domain', 'created_date']
	readonly_fields = ['kerberos_principal_name', 'kerberos_principal_created_date',
			'kerberos_principal_created']
	fieldsets = (
		('Owner Information', {
			'fields' : ( 'owner', 'location', 'description' )
		}),
		('Hardware Information', {
			'fields' : ( ('brand', 'model'), 'serial_number', 'host_type' )
		}),
		('Kerberos Information', {
			'description' : 'If this host is a member of the LDAP domain, you need to tick the request kerberos principal checkbox. A principal will then be created for the host.',
#			'classes' : [ 'collapse' ],
			'fields' : ( 'request_kerberos_principal', 'kerberos_principal_created',
				('kerberos_principal_name', 'kerberos_principal_created_date'))
		}),
#		('Domain Information', {
#			'fields' : ('host_domains' )
#		})
	)

class Ip4AddressInline(admin.TabularInline):
	model = Ip4Address
	extra = 0
	readonly_fields = ['address']

class SubnetAdmin(admin.ModelAdmin):
	list_display = ['name', 'network', 'netmask', 'num_addresses', 'broadcast_address', 'first_address', 'last_address']
	inlines = [Ip4AddressInline]

class DomainSrvRecordInline(admin.TabularInline):
	model = DomainSrvRecord
	extra = 0

class DomainTxtRecordInline(admin.TabularInline):
	model = DomainTxtRecord
	extra = 0

class DomainCnameRecordInline(admin.TabularInline):
	model = DomainCnameRecord
	extra = 0

class DomainAdmin(admin.ModelAdmin):
	inlines = [DomainSrvRecordInline, DomainTxtRecordInline, DomainCnameRecordInline]
	list_display = ['domain_name', 'domain_soa', 'domain_admin', 'num_records', 'domain_ipaddr']


class HostTypeAdmin(admin.ModelAdmin):
	list_display = ['host_type', 'description', 'num_members']

admin.site.register(Domain, DomainAdmin)
admin.site.register(Host, HostAdmin)
admin.site.register(Ip4Subnet, SubnetAdmin)
admin.site.register(Nameserver)
admin.site.register(MailExchange)
admin.site.register(HostType, HostTypeAdmin)
