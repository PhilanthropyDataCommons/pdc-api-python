from pdc_api_client.client import get_changemaker, get_organization_by_keycloak_id
from pdc_api_client.models import Source
from pdc_api_client.seeding.pdc_entities import (
    seed_changemaker,
    seed_fiscal_sponsorship,
    seed_funder,
    seed_source,
)


class TestRelaxOrganizationNullableRoles:
    def test_single_role_org_has_null_unfilled_roles(self, api_session, fresh_keycloak_org):
        seed_funder(api_session, keycloak_organization_id=fresh_keycloak_org.id)

        org = get_organization_by_keycloak_id(api_session, keycloak_id=fresh_keycloak_org.id)

        assert org.funder is not None
        assert org.changemaker is None
        assert org.data_provider is None


class TestFlattenSource:
    def test_funder_source_exposes_flat_funder_field(self, api_session):
        funder = seed_funder(api_session)
        source = seed_source(api_session, funder_short_code=funder.short_code)

        assert isinstance(source, Source)
        assert source.funder is not None
        assert source.funder.short_code == funder.short_code

    def test_changemaker_source_exposes_flat_changemaker_fields(self, api_session):
        changemaker = seed_changemaker(api_session)
        source = seed_source(api_session, changemaker_id=changemaker.id)

        assert source.changemaker_id == changemaker.id
        assert source.changemaker is not None
        assert source.funder is None


class TestDefaultArraysToEmpty:
    def test_fiscal_sponsors_omitted_for_caller_without_view_is_empty(
        self,
        api_session,
        add_user_to_org,
        fresh_keycloak_org,
        session_narrowed_to,
    ):
        sponsee = seed_changemaker(api_session)
        seed_fiscal_sponsorship(api_session, sponsee=sponsee, sponsor=seed_changemaker(api_session))
        username = f"{fresh_keycloak_org.alias}@example.com"
        add_user_to_org(username, fresh_keycloak_org)

        changemaker = get_changemaker(
            session_narrowed_to(username, fresh_keycloak_org.alias), changemaker_id=sponsee.id
        )

        assert changemaker.fiscal_sponsors == []
