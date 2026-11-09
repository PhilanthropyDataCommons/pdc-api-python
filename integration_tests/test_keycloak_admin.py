import uuid

import pytest

from pdc_api_client.seeding.keycloak_admin import KeycloakOrganization, KeycloakUser

TEST_USER_PASSWORD = "integration-test-password"


@pytest.fixture
def suffix() -> str:
    return uuid.uuid4().hex[:8]


class TestOrganizations:
    def test_ensure_organization_creates_then_finds_existing(self, keycloak_admin, suffix):
        alias = f"pkg-org-{suffix}"
        created = keycloak_admin.ensure_organization(
            name=f"Pkg Org {suffix}", alias=alias, domain=f"{alias}.example.com"
        )
        assert isinstance(created, KeycloakOrganization)
        assert created.alias == alias

        again = keycloak_admin.ensure_organization(name="ignored", alias=alias, domain=f"{alias}.example.com")
        assert again.id == created.id

    def test_get_organization_returns_existing_and_none(self, keycloak_admin, suffix):
        alias = f"pkg-getorg-{suffix}"
        assert keycloak_admin.get_organization(alias=alias) is None

        created = keycloak_admin.ensure_organization(
            name=f"Pkg Get {suffix}", alias=alias, domain=f"{alias}.example.com"
        )
        found = keycloak_admin.get_organization(alias=alias)
        assert found is not None
        assert found.id == created.id


class TestUsers:
    def test_ensure_user_creates_then_finds_existing(self, keycloak_admin, suffix):
        # registrationEmailAsUsername=true on the realm, so username == email.
        email = f"pkg-user-{suffix}@example.com"
        created = keycloak_admin.ensure_user(username=email, email=email, password=TEST_USER_PASSWORD)
        assert isinstance(created, KeycloakUser)
        assert created.id

        again = keycloak_admin.ensure_user(username=email, email=email, password=TEST_USER_PASSWORD)
        assert again.id == created.id


class TestMemberships:
    def test_add_is_idempotent_and_remove_reports_change(self, keycloak_admin, suffix):
        alias = f"pkg-mem-{suffix}"
        org = keycloak_admin.ensure_organization(name=f"Pkg Mem {suffix}", alias=alias, domain=f"{alias}.example.com")
        email = f"pkg-mem-user-{suffix}@example.com"
        user = keycloak_admin.ensure_user(username=email, email=email, password=TEST_USER_PASSWORD)

        assert keycloak_admin.ensure_user_in_organization(organization_id=org.id, user_id=user.id) is True
        assert keycloak_admin.ensure_user_in_organization(organization_id=org.id, user_id=user.id) is False

        assert keycloak_admin.remove_user_from_organization(organization_id=org.id, user_id=user.id) is True
        assert keycloak_admin.remove_user_from_organization(organization_id=org.id, user_id=user.id) is False


class TestClientConfig:
    def test_ensure_oidc_login_enabled_merges_redirect_uri(self, keycloak_admin, keycloak_client_id):
        # A fixed URI keeps repeated runs on a persistent stack from growing redirectUris.
        uri = "http://localhost:8000/pkg-integration-test/callback"
        keycloak_admin.ensure_oidc_login_enabled(client_id=keycloak_client_id, redirect_uris=[uri])

        client = keycloak_admin._find_client(keycloak_client_id)
        assert client.get("standardFlowEnabled") is True
        assert uri in client.get("redirectUris", [])

        keycloak_admin.ensure_oidc_login_enabled(client_id=keycloak_client_id, redirect_uris=[uri])
        assert uri in keycloak_admin._find_client(keycloak_client_id).get("redirectUris", [])

    def test_ensure_client_secret_sets_and_is_idempotent(self, keycloak_admin, keycloak_client_id):
        # The shared session fixtures authenticate with the original secret.
        target = keycloak_admin._find_client(keycloak_client_id)
        original = keycloak_admin._admin.get_client_secrets(target["id"])["value"]
        try:
            assert keycloak_admin.ensure_client_secret(client_id=keycloak_client_id, secret="pkg-int-secret") is True
            assert keycloak_admin._admin.get_client_secrets(target["id"])["value"] == "pkg-int-secret"
            assert keycloak_admin.ensure_client_secret(client_id=keycloak_client_id, secret="pkg-int-secret") is False
        finally:
            keycloak_admin.ensure_client_secret(client_id=keycloak_client_id, secret=original)

    def test_direct_grants_enable_is_idempotent(self, keycloak_admin, keycloak_client_id):
        keycloak_admin.set_direct_grants_enabled(client_id=keycloak_client_id, enabled=False)
        assert keycloak_admin.is_direct_grants_enabled(client_id=keycloak_client_id) is False

        keycloak_admin.ensure_direct_grants_enabled(client_id=keycloak_client_id)
        assert keycloak_admin.is_direct_grants_enabled(client_id=keycloak_client_id) is True

        keycloak_admin.ensure_direct_grants_enabled(client_id=keycloak_client_id)
        assert keycloak_admin.is_direct_grants_enabled(client_id=keycloak_client_id) is True
