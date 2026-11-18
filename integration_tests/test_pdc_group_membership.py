import uuid

import pytest

from pdc_api_client.client import get_changemaker
from pdc_api_client.models import PermissionGrantEntityType, PermissionGrantVerb
from pdc_api_client.permission_grants import (
    ChangemakerPermissionGrant,
    PermissionGrantGranteeType,
    create_permission_grant,
    delete_permission_grant,
)
from pdc_api_client.seeding.pdc_entities import seed_changemaker
from pdc_api_client.transport import APISession


def _can_manage(session: APISession, changemaker_id: int) -> bool:
    permissions = get_changemaker(session, changemaker_id=changemaker_id).permissions
    return PermissionGrantVerb.MANAGE in permissions.get(PermissionGrantEntityType.CHANGEMAKER, [])


@pytest.fixture()
def user_in_two_orgs(keycloak_admin, keycloak_client_id, test_user_password):
    suffix = uuid.uuid4().hex[:8]
    keycloak_admin.ensure_direct_grants_enabled(client_id=keycloak_client_id)
    org_a, org_b = (
        keycloak_admin.ensure_organization(
            name=f"Membership {suffix} {label}",
            alias=f"membership-{suffix}-{label}",
            domain=f"membership-{suffix}-{label}.example.com",
        )
        for label in ("a", "b")
    )
    username = f"membership-{suffix}@example.com"
    user = keycloak_admin.ensure_user(username=username, email=username, password=test_user_password)
    for org in (org_a, org_b):
        keycloak_admin.ensure_user_in_organization(organization_id=org.id, user_id=user.id)
    return username, org_a, org_b


@pytest.fixture()
def changemaker_managed_by(api_session):
    grant_ids = []

    def create(org_id: str) -> int:
        changemaker = seed_changemaker(api_session)
        grant = create_permission_grant(
            api_session,
            spec=ChangemakerPermissionGrant(
                changemaker_id=changemaker.id,
                grantee_type=PermissionGrantGranteeType.USER_GROUP,
                grantee_keycloak_organization_id=uuid.UUID(org_id),
                verbs=[PermissionGrantVerb.MANAGE],
                scope=[PermissionGrantEntityType.ANY],
            ),
        )
        assert grant.id is not None
        grant_ids.append(grant.id)
        return changemaker.id

    yield create
    for grant_id in grant_ids:
        delete_permission_grant(api_session, grant_id=grant_id)


@pytest.mark.xfail(
    strict=True,
    reason="PhilanthropyDataCommons/service#2617: a token's user-group grants leak into the user's other tokens",
)
def test_permissions_follow_only_the_current_tokens_org(user_in_two_orgs, changemaker_managed_by, session_narrowed_to):
    username, org_a, org_b = user_in_two_orgs
    changemaker_id = changemaker_managed_by(org_a.id)
    as_b = session_narrowed_to(username, org_b.alias)

    assert not _can_manage(as_b, changemaker_id)

    _can_manage(session_narrowed_to(username, org_a.alias), changemaker_id)

    assert not _can_manage(as_b, changemaker_id)
