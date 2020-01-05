import io

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from mdb.pxe import render_pxelinux_cfg
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from mdb.models import Host, OperatingSystem


class MyAPITestCases(APITestCase):
    fixtures = ['test_data']

    def create_user_with_token(self):
        self.user = User.objects.create(username='admin')
        self.token = Token.objects.create(user=self.user)
        self.host = Host.objects.first()

    def setUp(self):
        self.create_user_with_token()
        return super(MyAPITestCases, self).setUp()

    def test_validate_puppet_host_by_secret(self):
        data = {
            'pxe_key': self.host.pxe_key,
            'certname': '{}.{}'.format(self.host.hostname, self.host.interface_set.first().domain.domain_name)
        }
        self.client.credentials(HTTP_AUTHORIZATION='Token {}'.format(self.token.key))
        res = self.client.post(reverse('api-validate-host-secret'), data, format='json')
        self.assertEquals(res.status_code, 200, res.content)
        self.assertFalse(Host.objects.get(pk=self.host.pk).pxe_installable)


class UnitTests(TestCase):
    fixtures = ['test_data']

    def test_render_pxeconfig(self):
        host = Host.objects.first()
        interface = host.interface_set.exclude(ip4address__isnull=True).first()
        config = render_pxelinux_cfg(interface, host)

        self.assertIn(settings.MDB_PXE_INITRD, config)
        self.assertIn(settings.MDB_PXE_KERNEL, config)
        self.assertIn(settings.MDB_PXE_PRESEED_URL, config)

    def test_render_pxeconfig_with_os_pxe_config(self):
        _os = OperatingSystem.objects.get(pk=2)  # OS with all pxe vars set
        Host.objects.filter(pk=Host.objects.first().pk).update(operating_system=_os)
        host = Host.objects.first()

        interface = host.interface_set.exclude(ip4address__isnull=True).first()
        config = render_pxelinux_cfg(interface, host)

        self.assertIn(_os.pxe_initrd, config)
        self.assertIn(_os.pxe_kernel, config)
        self.assertIn(_os.pxe_preseed_config_url, config)

    def test_host_as_pxe_files(self):
        host = Host.objects.first()
        self.assertEqual(len(host.as_pxe_files()), 1)


class RunManagementCommands(TestCase):
    fixtures = ['test_data']

    def test_zone_sync(self):
        # expected_zone_file = ''
        with io.BytesIO() as f:
            call_command('zone-sync', debug=True, stdout=f)
        # TODO check expected_zone_file

    def test_dhcp_sync(self):
        # expected_dhcp_file = ''
        with io.BytesIO() as f:
            call_command('dhcp-sync', stdout=f)
        # TODO check expected_dhcp_file
