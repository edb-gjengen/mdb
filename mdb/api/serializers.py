from __future__ import unicode_literals
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from mdb.models import Host


class HostPXEValidateSerializer(serializers.Serializer):
    certname = serializers.CharField(required=True)
    pxe_key = serializers.CharField(required=True)
    host = None

    def _get_host_by_fqdn(self, attrs):
        fqdn = attrs['certname']
        host_name = fqdn.split('.')[0]
        domain = '.'.join(fqdn.split('.')[1:])

        try:
            return Host.objects.get(hostname=host_name, interface__domain__domain_name=domain)
        except (Host.DoesNotExist, Host.MultipleObjectsReturned):
            return None

    def validate(self, attrs):
        # custom validation
        host = self._get_host_by_fqdn(attrs)

        if host is None:
            raise ValidationError('Host \'{}\' not found.'.format(attrs['certname']))

        if not host.pxe_installable:
            raise ValidationError('Host \'{}\' is marked as not installable via PXE.'.format(attrs['certname']))

        if not host.pxe_key:
            raise ValidationError('Host \'{}\' has no pxe_key.'.format(attrs['certname']))

        if host.pxe_key != attrs['pxe_key']:
            raise ValidationError('Supplied pxe_key \'{}\' does not match host \'{}\'.'.format(
                    attrs['pxe_key'],
                    attrs['certname']))

        self.host = host

        return attrs

    def create(self, validated_data):
        # Make requests kind of idempotent by only allowing 1 request / installation
        self.host.pxe_installable = False
        self.host.pxe_key = ''
        self.host.save()

        return self.host
