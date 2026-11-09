import uuid

import pytest

from pdc_api_client.seeding.pdc_entities import (
    ensure_changemaker_for_kc_org,
    ensure_data_provider_for_kc_org,
    ensure_funder_for_kc_org,
)


@pytest.fixture
def fresh_kc_org(keycloak_admin):
    suffix = uuid.uuid4().hex[:8]
    alias = f"ensure-test-{suffix}"
    return keycloak_admin.ensure_organization(
        name=f"Ensure Test {suffix}",
        alias=alias,
        domain=f"{alias}.example.com",
    )


def test_ensure_funder_for_kc_org_is_idempotent(api_session, fresh_kc_org):
    first = ensure_funder_for_kc_org(api_session, kc_org=fresh_kc_org, name="X Funder")
    second = ensure_funder_for_kc_org(api_session, kc_org=fresh_kc_org, name="X Funder")
    assert first.short_code == second.short_code
    assert str(first.keycloak_organization_id) == fresh_kc_org.id


def test_ensure_changemaker_for_kc_org_is_idempotent(api_session, fresh_kc_org):
    first = ensure_changemaker_for_kc_org(api_session, kc_org=fresh_kc_org, name="X Changemaker")
    second = ensure_changemaker_for_kc_org(api_session, kc_org=fresh_kc_org, name="X Changemaker")
    assert first.id == second.id
    assert str(first.keycloak_organization_id) == fresh_kc_org.id


def test_ensure_data_provider_for_kc_org_is_idempotent(api_session, fresh_kc_org):
    first = ensure_data_provider_for_kc_org(api_session, kc_org=fresh_kc_org, name="X Data Provider")
    second = ensure_data_provider_for_kc_org(api_session, kc_org=fresh_kc_org, name="X Data Provider")
    assert first.short_code == second.short_code
    assert str(first.keycloak_organization_id) == fresh_kc_org.id
