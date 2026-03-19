import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from mdb.models import Host


@pytest.fixture
def db_with_fixtures(db):
    call_command("loaddata", "test_data", verbosity=0)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_with_token(db_with_fixtures):
    user = User.objects.create(username="admin")
    token = Token.objects.create(user=user)
    return user, token


@pytest.fixture
def host(db_with_fixtures):
    return Host.objects.first()


@pytest.mark.django_db
def test_validate_puppet_host_by_secret(api_client, user_with_token, host):
    _, token = user_with_token
    data = {
        "pxe_key": host.pxe_key,
        "certname": "{}.{}".format(
            host.hostname, host.interface_set.first().domain.domain_name
        ),
    }
    api_client.credentials(HTTP_AUTHORIZATION="Token {}".format(token.key))
    res = api_client.post(reverse("api-validate-host-secret"), data, format="json")
    assert res.status_code == 200, res.content
    assert not Host.objects.get(pk=host.pk).pxe_installable
