import ipaddress

from django.db import migrations


def set_classless_reverse_names(apps, schema_editor):
    """Recompute domain_name for sub-/24 IPv4 subnets (RFC 2317 classless).

    domain_name is frozen on first save, so subnets created before classless
    support kept the plain /24 name (190.36.158.in-addr.arpa) even for a /26.
    That apex no longer matches the classless zone declared in named.conf, so
    BIND refuses to load the file.  Rewrite those names to the RFC 2317 form
    (192-26.190.36.158.in-addr.arpa).  /24-or-shorter subnets are left alone.
    """
    Ip4Subnet = apps.get_model("mdb", "Ip4Subnet")
    for subnet in Ip4Subnet.objects.all():
        try:
            net = ipaddress.IPv4Network(
                "%s/%s" % (subnet.network, subnet.netmask), strict=False
            )
        except ValueError:
            continue
        if net.prefixlen <= 24:
            continue
        o1, o2, o3, o4 = str(net.network_address).split(".")
        name = "%s-%d.%s.%s.%s.in-addr.arpa" % (o4, net.prefixlen, o3, o2, o1)
        if subnet.domain_name != name:
            subnet.domain_name = name
            subnet.save(update_fields=["domain_name"])


class Migration(migrations.Migration):
    dependencies = [
        ("mdb", "0013_host_allow_email"),
    ]

    operations = [
        migrations.RunPython(set_classless_reverse_names, migrations.RunPython.noop),
    ]
