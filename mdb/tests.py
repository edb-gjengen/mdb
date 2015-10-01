from django.core.urlresolvers import reverse
from rest_framework.test import APITestCase


class APITestCases(APITestCase):
    def test_validate_puppet_host_by_secret(self):
        data = {
            'secret': 'something',
            'certname': 'arnold.neuf.no'
        }
        res = self.client.post(reverse('api-validate-host-secret'), data)
        self.fail()
