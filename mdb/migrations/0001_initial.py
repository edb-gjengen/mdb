# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import re
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DhcpConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('serial', models.IntegerField()),
                ('active_serial', models.IntegerField()),
                ('name', models.CharField(max_length=255)),
                ('authoritative', models.BooleanField(default=False)),
                ('ddns_update_style', models.CharField(max_length=63)),
                ('default_lease_time', models.IntegerField(default=600)),
                ('max_lease_time', models.IntegerField(default=7200)),
                ('log_facility', models.CharField(max_length=255)),
            ],
            options={
                'verbose_name': 'DHCP config',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DhcpCustomField',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DhcpOption',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(max_length=255)),
                ('value', models.CharField(max_length=255)),
            ],
            options={
                'verbose_name': 'DHCP option',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Domain',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('domain_name', models.CharField(max_length=256)),
                ('domain_soa', models.CharField(max_length=256)),
                ('domain_ttl', models.IntegerField(default=60)),
                ('domain_serial', models.IntegerField(default=1)),
                ('domain_active_serial', models.IntegerField(default=0, editable=False)),
                ('domain_refresh', models.IntegerField(default=28800)),
                ('domain_retry', models.IntegerField(default=7200)),
                ('domain_expire', models.IntegerField(default=604800)),
                ('domain_minimum_ttl', models.IntegerField(default=86400)),
                ('domain_admin', models.EmailField(max_length=75)),
                ('domain_ipaddr', models.IPAddressField()),
                ('domain_filename', models.CharField(max_length=256)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DomainARecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('target', models.CharField(max_length=256)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('domain', models.ForeignKey(to='mdb.Domain', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DomainCnameRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('target', models.CharField(max_length=256)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('domain', models.ForeignKey(to='mdb.Domain', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DomainSrvRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('srvce', models.CharField(max_length=64)),
                ('prot', models.CharField(max_length=64)),
                ('name', models.CharField(max_length=128)),
                ('priority', models.IntegerField()),
                ('weight', models.IntegerField()),
                ('port', models.IntegerField()),
                ('target', models.CharField(max_length=256)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('domain', models.ForeignKey(to='mdb.Domain', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DomainTxtRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('target', models.CharField(max_length=256)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('domain', models.ForeignKey(to='mdb.Domain', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Host',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('location', models.CharField(max_length=1024)),
                ('brand', models.CharField(max_length=1024)),
                ('model', models.CharField(max_length=1024)),
                ('owner', models.CharField(max_length=1024)),
                ('hostname', models.CharField(max_length=64, validators=[django.core.validators.RegexValidator(re.compile(b'^(?!-)[-a-z0-9]+(?<!-)$', 2), 'Enter a valid hostname', b'invalid')])),
                ('serial_number', models.CharField(max_length=256)),
                ('description', models.CharField(max_length=1024)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('virtual', models.BooleanField(default=False)),
                ('request_kerberos_principal', models.BooleanField(default=False)),
                ('kerberos_principal_created', models.BooleanField(default=False, editable=False)),
                ('kerberos_principal_name', models.CharField(max_length=256, editable=False)),
                ('kerberos_principal_created_date', models.DateTimeField(null=True, editable=False, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='HostType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('host_type', models.CharField(max_length=64)),
                ('description', models.CharField(max_length=1024)),
            ],
            options={
                'ordering': ('host_type',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Interface',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('macaddr', models.CharField(max_length=17)),
                ('pxe_filename', models.CharField(max_length=64, blank=True)),
                ('dhcp_client', models.BooleanField(default=False)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('domain', models.ForeignKey(to='mdb.Domain', on_delete=models.CASCADE)),
                ('host', models.ForeignKey(to='mdb.Host', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Ip4Address',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.IPAddressField()),
                ('last_contact', models.DateTimeField()),
                ('ping_avg_rtt', models.FloatField()),
            ],
            options={
                'verbose_name': 'IPv4 address',
                'verbose_name_plural': 'IPv4 addresses',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Ip4Subnet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('netmask', models.IPAddressField()),
                ('network', models.IPAddressField()),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('domain_name', models.CharField(max_length=255, editable=False)),
                ('domain_soa', models.CharField(max_length=256)),
                ('domain_ttl', models.IntegerField(default=60)),
                ('domain_serial', models.IntegerField(default=1)),
                ('domain_active_serial', models.IntegerField(default=0, editable=False)),
                ('domain_refresh', models.IntegerField(default=28800)),
                ('domain_retry', models.IntegerField(default=7200)),
                ('domain_expire', models.IntegerField(default=604800)),
                ('domain_minimum_ttl', models.IntegerField(default=86400)),
                ('domain_admin', models.EmailField(max_length=75)),
                ('domain_filename', models.CharField(max_length=256)),
                ('dhcp_dynamic', models.BooleanField(default=False)),
                ('dhcp_dynamic_start', models.IPAddressField(null=True, blank=True)),
                ('dhcp_dynamic_end', models.IPAddressField(null=True, blank=True)),
                ('dhcp_config', models.ForeignKey(to='mdb.DhcpConfig', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'IPv4 subnet',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Ip6Address',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.CharField(max_length=64)),
                ('interface', models.ForeignKey(to='mdb.Interface', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'IPv6 address',
                'verbose_name_plural': 'IPv6 addresses',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Ip6Subnet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('network', models.CharField(max_length=255)),
                ('netmask', models.IntegerField(default=64)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('domain_name', models.CharField(max_length=255, editable=False)),
                ('domain_soa', models.CharField(max_length=255)),
                ('domain_ttl', models.IntegerField(default=60)),
                ('domain_serial', models.IntegerField(default=1)),
                ('domain_active_serial', models.IntegerField(default=0, editable=False)),
                ('domain_refresh', models.IntegerField(default=28800)),
                ('domain_retry', models.IntegerField(default=7200)),
                ('domain_expire', models.IntegerField(default=604800)),
                ('domain_minimum_ttl', models.IntegerField(default=86400)),
                ('domain_admin', models.EmailField(max_length=75)),
                ('domain_filename', models.CharField(max_length=256)),
            ],
            options={
                'verbose_name': 'IPv6 subnet',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MailExchange',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('priority', models.IntegerField()),
                ('hostname', models.CharField(max_length=256)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Nameserver',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('hostname', models.CharField(max_length=256)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OperatingSystem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('version', models.CharField(max_length=64)),
            ],
            options={
                'ordering': ('name', 'version'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OsArchitecture',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('architecture', models.CharField(max_length=64)),
            ],
            options={
                'verbose_name': 'OS architecture',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='operatingsystem',
            name='architecture',
            field=models.ForeignKey(to='mdb.OsArchitecture', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='ip6subnet',
            name='domain_nameservers',
            field=models.ManyToManyField(to='mdb.Nameserver'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='ip6address',
            name='subnet',
            field=models.ForeignKey(to='mdb.Ip6Subnet', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='ip4subnet',
            name='domain_nameservers',
            field=models.ManyToManyField(to='mdb.Nameserver'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='ip4address',
            name='subnet',
            field=models.ForeignKey(to='mdb.Ip4Subnet', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='interface',
            name='ip4address',
            field=models.ForeignKey(null=True, blank=True, to='mdb.Ip4Address', unique=True, on_delete=models.SET_NULL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='host',
            name='host_type',
            field=models.ForeignKey(to='mdb.HostType', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='host',
            name='operating_system',
            field=models.ForeignKey(to='mdb.OperatingSystem', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='domain',
            name='domain_mailexchanges',
            field=models.ManyToManyField(to='mdb.MailExchange'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='domain',
            name='domain_nameservers',
            field=models.ManyToManyField(to='mdb.Nameserver'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='dhcpoption',
            name='ip4subnet',
            field=models.ForeignKey(to='mdb.Ip4Subnet', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='dhcpcustomfield',
            name='ip4subnet',
            field=models.ForeignKey(to='mdb.Ip4Subnet', on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
