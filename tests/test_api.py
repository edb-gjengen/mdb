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
        "certname": f"{host.hostname}.{host.interface_set.first().domain.domain_name}",
    }
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    res = api_client.post(reverse("api-validate-host-secret"), data, format="json")
    assert res.status_code == 200, res.content
    assert not Host.objects.get(pk=host.pk).pxe_installable


def post_validate(api_client, token, certname, pxe_key):
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client.post(
        reverse("api-validate-host-secret"),
        {"certname": certname, "pxe_key": pxe_key},
        format="json",
    )


@pytest.mark.parametrize(
    ("change", "certname", "error"),
    [
        ({}, "nosuchhost.edb.technology", "not found"),
        ({}, "tut.nosuchdomain.example", "not found"),
        ({"pxe_installable": False}, "tut.edb.technology", "not installable"),
        ({"pxe_key": ""}, "tut.edb.technology", "has no pxe_key"),
    ],
)
def test_validate_rejects(api_client, user_with_token, host, change, certname, error):
    _, token = user_with_token
    Host.objects.filter(pk=host.pk).update(**change)

    res = post_validate(api_client, token, certname, host.pxe_key)

    assert res.status_code == 400
    assert error in str(res.content)


def test_validate_rejects_wrong_key(api_client, user_with_token, host):
    _, token = user_with_token
    res = post_validate(api_client, token, "tut.edb.technology", "wrong")
    assert res.status_code == 400
    assert "does not match" in str(res.content)
    # A wrong guess must not use up the installation.
    host.refresh_from_db()
    assert host.pxe_installable
    assert host.pxe_key


def test_validate_key_works_only_once(api_client, user_with_token, host):
    _, token = user_with_token
    key = host.pxe_key
    assert (
        post_validate(api_client, token, "tut.edb.technology", key).status_code == 200
    )
    assert (
        post_validate(api_client, token, "tut.edb.technology", key).status_code == 400
    )


def test_validate_requires_a_token(api_client, host):
    res = api_client.post(
        reverse("api-validate-host-secret"),
        {"certname": "tut.edb.technology", "pxe_key": host.pxe_key},
        format="json",
    )
    assert res.status_code == 401
    assert Host.objects.get(pk=host.pk).pxe_installable
