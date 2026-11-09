import uuid

import pytest

from pdc_api_client.client import get_changemaker, get_organization_by_keycloak_id
from pdc_api_client.models import Source
from pdc_api_client.seeding.pdc_entities import (
    seed_changemaker,
    seed_fiscal_sponsorship,
    seed_funder,
    seed_source,
)


@pytest.fixture
def fresh_kc_org(keycloak_admin):
    suffix = uuid.uuid4().hex[:8]
    alias = f"preprocess-{suffix}"
    return keycloak_admin.ensure_organization(
        name=f"Preprocess Test {suffix}",
        alias=alias,
        domain=f"{alias}.example.com",
    )


class TestOrganizationRoles:
    # Covers codegen/preprocess.py::relax_organization_nullable_roles.
    def test_single_role_org_has_null_unfilled_roles(self, api_session, fresh_kc_org):
        seed_funder(api_session, keycloak_organization_id=fresh_kc_org.id)

        org = get_organization_by_keycloak_id(api_session, keycloak_id=fresh_kc_org.id)

        assert org.funder is not None
        assert org.changemaker is None
        assert org.data_provider is None


class TestFlattenSource:
    # Covers codegen/preprocess.py::flatten_source.
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
    # Covers codegen/preprocess.py::default_arrays_to_empty.
    def test_fiscal_sponsors_omitted_for_caller_without_view_is_empty(
        self, api_session, keycloak_admin, keycloak_client_id, test_user_password, fresh_kc_org, session_narrowed_to
    ):
        sponsee = seed_changemaker(api_session)
        seed_fiscal_sponsorship(api_session, sponsee=sponsee, sponsor=seed_changemaker(api_session))
        keycloak_admin.ensure_direct_grants_enabled(client_id=keycloak_client_id)
        username = f"{fresh_kc_org.alias}@example.com"
        user = keycloak_admin.ensure_user(username=username, email=username, password=test_user_password)
        keycloak_admin.ensure_user_in_organization(organization_id=fresh_kc_org.id, user_id=user.id)

        changemaker = get_changemaker(session_narrowed_to(username, fresh_kc_org.alias), changemaker_id=sponsee.id)

        assert changemaker.fiscal_sponsors == []
