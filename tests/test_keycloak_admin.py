import pytest
import responses

from pdc_api_client.seeding.keycloak_admin import KeycloakAdmin

KEYCLOAK_URL = "https://keycloak.test"
ORGANIZATIONS_URL = f"{KEYCLOAK_URL}/admin/realms/pdc/organizations"


def test_ensure_organization_raises_when_keycloak_returns_no_id():
    responses.post(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        json={"access_token": "token", "expires_in": 300, "refresh_token": "refresh", "refresh_expires_in": 1800},
    )
    responses.get(ORGANIZATIONS_URL, json=[])
    responses.post(ORGANIZATIONS_URL, status=201)
    admin = KeycloakAdmin(keycloak_url=KEYCLOAK_URL, realm="pdc", admin_username="admin", admin_password="secret")

    with pytest.raises(LookupError, match="acme"):
        admin.ensure_organization(name="Acme", alias="acme", domain="acme.test")
