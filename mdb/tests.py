from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from mdb.models import Host
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


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
