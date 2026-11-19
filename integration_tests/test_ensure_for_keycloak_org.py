from pdc_api_client.seeding.pdc_entities import (
    ensure_changemaker_for_keycloak_org,
    ensure_data_provider_for_keycloak_org,
    ensure_funder_for_keycloak_org,
)


class TestEnsureFunderForKeycloakOrg:
    def test_is_idempotent(self, api_session, fresh_keycloak_org):
        first = ensure_funder_for_keycloak_org(api_session, keycloak_org=fresh_keycloak_org, name="Ensure Test Funder")
        second = ensure_funder_for_keycloak_org(api_session, keycloak_org=fresh_keycloak_org, name="Ensure Test Funder")
        assert first.short_code == second.short_code
        assert str(first.keycloak_organization_id) == fresh_keycloak_org.id


class TestEnsureChangemakerForKeycloakOrg:
    def test_is_idempotent(self, api_session, fresh_keycloak_org):
        first = ensure_changemaker_for_keycloak_org(
            api_session, keycloak_org=fresh_keycloak_org, name="Ensure Test Changemaker"
        )
        second = ensure_changemaker_for_keycloak_org(
            api_session, keycloak_org=fresh_keycloak_org, name="Ensure Test Changemaker"
        )
        assert first.id == second.id
        assert str(first.keycloak_organization_id) == fresh_keycloak_org.id


class TestEnsureDataProviderForKeycloakOrg:
    def test_is_idempotent(self, api_session, fresh_keycloak_org):
        first = ensure_data_provider_for_keycloak_org(
            api_session, keycloak_org=fresh_keycloak_org, name="Ensure Test Data Provider"
        )
        second = ensure_data_provider_for_keycloak_org(
            api_session, keycloak_org=fresh_keycloak_org, name="Ensure Test Data Provider"
        )
        assert first.short_code == second.short_code
        assert str(first.keycloak_organization_id) == fresh_keycloak_org.id
