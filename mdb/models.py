from django.db import models
from django.db.models.signals import post_save
from django.db.models.signals import pre_delete
from django.dispatch import receiver

import ipaddr
import datetime

# Create your models here.

class Nameserver(models.Model):
	hostname = models.CharField(max_length=256)
	
	def __unicode__(self):
		return self.hostname

class MailExchange(models.Model):
	priority = models.IntegerField()
	hostname = models.CharField(max_length=256)

	def __unicode__(self):
		return "(" + str(self.priority) + ") " + self.hostname

class Domain(models.Model):
	domain_name = models.CharField(max_length=256)
	domain_soa = models.CharField(max_length=256)
	domain_ttl = models.IntegerField(default=60)
	domain_serial = models.IntegerField(default=2011010101)
	domain_refresh = models.IntegerField(default=28800)
	domain_retry = models.IntegerField(default=7200)
	domain_expire = models.IntegerField(default=604800)
	domain_minimum_ttl = models.IntegerField(default=86400)
	domain_admin = models.EmailField()
	domain_ipaddr = models.IPAddressField()
	domain_filename = models.CharField(max_length=256)
	created_date = models.DateTimeField(auto_now_add=True)

	domain_nameservers = models.ManyToManyField(Nameserver)
	domain_mailexchanges = models.ManyToManyField(MailExchange)

	def __unicode__(self):
		return self.domain_name

	def num_records(self):
		size = {}
		size["cname"] = self.domaincnamerecord_set.count()
		size["srv"] = self.domainsrvrecord_set.count()
		size["txt"] = self.domaintxtrecord_set.count()
		size["a"]   = self.host_set.count()
		return size

	num_records.short_description = "Num Records"

	def zone_file_contents(self):
		content = "; zone file for %s\n" % self.domain_name
		content += "; %s\n" % datetime.datetime.now()
		content += ": filename: %s\n" % self.domain_filename
		content += "$TTL %s\n" % self.domain_ttl
		content += "@ IN SOA %s. %s. (\n" % (self.domain_soa, self.domain_admin.replace("@", "."))
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
		
		content += "; SRV records\n"

		for srv in self.domainsrvrecord_set.all():
			content += unicode(srv) + "\n"

		content += "; CNAME records \n"
		
		for cname in self.domaincnamerecord_set.all():
			content += "%s\tIN\tCNAME\t%s\n" % (cname.name, cname.target)
		
		content += "; TXT records \n"

		for txt in self.domaintxtrecord_set.all():
			content += unicode(txt) + "\n"

		for host in self.host_set.all():
			if host.interface_set.count() > 0:
				content += "%s" % host.hostname
				for interface in host.interface_set.all():
					content += "\t\tIN\tA\t%s\n" % interface.ip4address.address
		
		return content	

class DomainSrvRecord(models.Model):
	srvce = models.CharField(max_length=64)
	prot = models.CharField(max_length=64)
	name = models.CharField(max_length=128)
	priority = models.IntegerField()
	weight = models.IntegerField()
	port = models.IntegerField()
	target = models.CharField(max_length=256)
	domain = models.ForeignKey(Domain)
	created_date = models.DateTimeField(auto_now_add=True)
	
	def __unicode__(self):
		return self.srvce + "." + self.prot + "." + self.name + ". IN SRV " \
			+ str(self.priority) + " " + str(self.weight) + " " + \
			str(self.port) + " " + self.target + "."

class DomainTxtRecord(models.Model):
	name = models.CharField(max_length=256)
	target = models.CharField(max_length=256)
	domain = models.ForeignKey(Domain)
	created_date = models.DateTimeField(auto_now_add=True)

	def __unicode__(self):
		return self.name + " TXT " + self.target

class DomainCnameRecord(models.Model):
	name = models.CharField(max_length=256)
	target = models.CharField(max_length=256)
	domain = models.ForeignKey(Domain)
	created_date = models.DateTimeField(auto_now_add=True)

	def __unicode__(self):
		return self.name + " IN CNAME " + self.target

class Ip4Subnet(models.Model):
	name = models.CharField(max_length=256)
	netmask = models.IPAddressField()
	network = models.IPAddressField()
	created_date = models.DateTimeField(auto_now_add=True)
	
	def __unicode__(self):
		return self.network + " (" + self.name + ")"

	def num_addresses(self):
		subnet = ipaddr.IPv4Network(self.network + "/" + self.netmask)
		return subnet.numhosts
	
	def broadcast_address(self):
		subnet = ipaddr.IPv4Network(self.network + "/" + self.netmask)
		return subnet.broadcast

	def first_address(self):
		subnet = ipaddr.IPv4Network(self.network + "/" + self.netmask)
		return subnet.iterhosts().next()

	def last_address(self):
		subnet = ipaddr.IPv4Network(self.network + "/" + self.netmask)
		for curr in subnet.iterhosts():
			pass # horribly ineficcient

		return curr

	
	broadcast_address.short_description = 'broadcast'
	num_addresses.short_description = '#addresses'
	first_address.short_description = 'first address'
	last_address.short_description = 'last address'


class Ip4Address(models.Model):
	subnet = models.ForeignKey(Ip4Subnet)
	address = models.IPAddressField()

	def __unicode__(self):
		return self.address

	def assigned_to_host(self):
		self.interface_set.get().host

	assigned_to_host.short_description = "Assigned to Host"

class HostType(models.Model):
	host_type = models.CharField(max_length=64)
	description = models.CharField(max_length=1024)

	def __unicode__(self):
		return self.host_type

	def num_members(self):
		return self.host_set.count()

class OsArchitecture(models.Model):
	architecture = models.CharField(max_length=64)

	def __unicode__(self):
		return self.architecture

class OperatingSystem(models.Model):
	name = models.CharField(max_length=256)
	version = models.CharField(max_length=64)
	architecture = models.ForeignKey(OsArchitecture)

	def __unicode__(self):
		return self.name + " " + self.version + " (" + unicode(self.architecture) + ")"

class Host(models.Model):
	domain = models.ManyToManyField(Domain)
	location = models.CharField(max_length=1024)
	brand = models.CharField(max_length=1024)
	model = models.CharField(max_length=1024)
	owner = models.CharField(max_length=1024)
	hostname = models.CharField(max_length=64)
	serial_number = models.CharField(max_length=256)
	description = models.CharField(max_length=1024)
	created_date = models.DateTimeField(auto_now_add=True)
	host_type = models.ForeignKey(HostType)
	virtual = models.BooleanField()
	operating_system = models.ForeignKey(OperatingSystem)

	request_kerberos_principal = models.BooleanField()
	kerberos_principal_created = models.BooleanField(editable=False)
	kerberos_principal_name = models.CharField(max_length = 256, editable=False)
	kerberos_principal_created_date = models.DateTimeField(null=True, blank=True, editable=False)

	def __unicode__(self):
		return self.hostname

	def in_domain(self):
		domains = []
		for d in self.domain.all():
			domains.append(unicode(d))
		return ",".join(domains)

	in_domain.short_description = "in domains"
			
		

class Interface(models.Model):
	name = models.CharField(max_length=128)
	macaddr = models.CharField(max_length=17)
	pxe_filename = models.CharField(max_length=64, blank=True)
	dhcp_client = models.BooleanField()
	host = models.ForeignKey(Host)
	ip4address = models.ForeignKey(Ip4Address, blank=True, null=True)
	created_date = models.DateTimeField(auto_now_add=True)
	
	def __unicode__(self):
		return self.macaddr

@receiver(post_save, sender=Ip4Subnet)
def create_ips_for_subnet(sender, instance, created, **kwargs):
	if not created:
		return
	
	subnet = ipaddr.IPv4Network(instance.network + "/" + instance.netmask)

	for addr in subnet.iterhosts():
		address = Ip4Address(address = str(addr), subnet=instance)
		address.save()
	
@receiver(pre_delete, sender=Ip4Subnet)
def delete_ips_for_subnet(sender, instance, **kwargs):
	
	for addr in instance.ip4address_set.all():
		addr.delete()
