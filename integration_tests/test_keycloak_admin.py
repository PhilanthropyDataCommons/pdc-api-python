from pdc_api.seeding.keycloak_admin import KeycloakOrganization, KeycloakUser


class TestEnsureOrganization:
    def test_creates_then_finds_existing(self, keycloak_admin, suffix):
        alias = f"keycloak-admin-test-org-{suffix}"
        created = keycloak_admin.ensure_organization(
            name=f"Keycloak Admin Test Org {suffix}", alias=alias, domain=f"{alias}.example.com"
        )
        assert isinstance(created, KeycloakOrganization)
        assert created.alias == alias

        again = keycloak_admin.ensure_organization(name="ignored", alias=alias, domain=f"{alias}.example.com")
        assert again.id == created.id


class TestGetOrganization:
    def test_returns_existing_and_none(self, keycloak_admin, suffix):
        alias = f"keycloak-admin-test-get-org-{suffix}"
        assert keycloak_admin.get_organization(alias=alias) is None

        created = keycloak_admin.ensure_organization(
            name=f"Keycloak Admin Test Get Org {suffix}", alias=alias, domain=f"{alias}.example.com"
        )
        found = keycloak_admin.get_organization(alias=alias)
        assert found is not None
        assert found.id == created.id


class TestEnsureUser:
    def test_creates_then_finds_existing(self, keycloak_admin, suffix, test_user_password):
        # registrationEmailAsUsername=true on the realm, so username == email.
        email = f"keycloak-admin-test-user-{suffix}@example.com"
        created = keycloak_admin.ensure_user(username=email, email=email, password=test_user_password)
        assert isinstance(created, KeycloakUser)
        assert created.id

        again = keycloak_admin.ensure_user(username=email, email=email, password=test_user_password)
        assert again.id == created.id


class TestUserOrganizationMembership:
    def test_add_is_idempotent_and_remove_reports_change(self, keycloak_admin, suffix, test_user_password):
        alias = f"keycloak-admin-test-membership-org-{suffix}"
        org = keycloak_admin.ensure_organization(
            name=f"Keycloak Admin Test Membership Org {suffix}", alias=alias, domain=f"{alias}.example.com"
        )
        email = f"keycloak-admin-test-member-{suffix}@example.com"
        user = keycloak_admin.ensure_user(username=email, email=email, password=test_user_password)

        assert keycloak_admin.ensure_user_in_organization(organization_id=org.id, user_id=user.id) is True
        assert keycloak_admin.ensure_user_in_organization(organization_id=org.id, user_id=user.id) is False

        assert keycloak_admin.remove_user_from_organization(organization_id=org.id, user_id=user.id) is True
        assert keycloak_admin.remove_user_from_organization(organization_id=org.id, user_id=user.id) is False


class TestEnsureOidcLoginEnabled:
    def test_merges_redirect_uri(self, keycloak_admin, keycloak_client_id):
        # A fixed URI keeps repeated runs on a persistent stack from growing redirectUris.
        uri = "http://localhost:8000/keycloak-admin-test/callback"
        keycloak_admin.ensure_oidc_login_enabled(client_id=keycloak_client_id, redirect_uris=[uri])

        client = keycloak_admin._find_client(keycloak_client_id)
        assert client.get("standardFlowEnabled") is True
        assert uri in client.get("redirectUris", [])

        keycloak_admin.ensure_oidc_login_enabled(client_id=keycloak_client_id, redirect_uris=[uri])
        assert uri in keycloak_admin._find_client(keycloak_client_id).get("redirectUris", [])


class TestEnsureClientSecret:
    def test_sets_and_is_idempotent(self, keycloak_admin, keycloak_client_id):
        # The shared session fixtures authenticate with the original secret.
        target = keycloak_admin._find_client(keycloak_client_id)
        original = keycloak_admin._admin.get_client_secrets(target["id"])["value"]
        try:
            assert (
                keycloak_admin.ensure_client_secret(client_id=keycloak_client_id, secret="keycloak-admin-test-secret")
                is True
            )
            assert keycloak_admin._admin.get_client_secrets(target["id"])["value"] == "keycloak-admin-test-secret"
            assert (
                keycloak_admin.ensure_client_secret(client_id=keycloak_client_id, secret="keycloak-admin-test-secret")
                is False
            )
        finally:
            keycloak_admin.ensure_client_secret(client_id=keycloak_client_id, secret=original)


class TestEnsureDirectGrantsEnabled:
    def test_is_idempotent(self, keycloak_admin, keycloak_client_id):
        keycloak_admin.set_direct_grants_enabled(client_id=keycloak_client_id, enabled=False)
        assert keycloak_admin.is_direct_grants_enabled(client_id=keycloak_client_id) is False

        keycloak_admin.ensure_direct_grants_enabled(client_id=keycloak_client_id)
        assert keycloak_admin.is_direct_grants_enabled(client_id=keycloak_client_id) is True

        keycloak_admin.ensure_direct_grants_enabled(client_id=keycloak_client_id)
        assert keycloak_admin.is_direct_grants_enabled(client_id=keycloak_client_id) is True
