import uuid
from uuid import UUID

import pytest

from pdc_api_client.errors import PDCNotFoundError
from pdc_api_client.models import BaseFieldCategory
from pdc_api_client.permission_grants import (
    ChangemakerPermissionGrant,
    FunderPermissionGrant,
    PermissionGrantConditionRule,
    PermissionGrantConditions,
    PermissionGrantEntityType,
    PermissionGrantGranteeType,
    PermissionGrantVerb,
    ProposalPermissionGrant,
    create_permission_grant,
    delete_permission_grant,
    get_permission_grant,
    list_permission_grants,
    update_permission_grant,
)
from pdc_api_client.seeding.pdc_entities import seed_changemaker, seed_funder, seed_proposal


@pytest.fixture()
def grantee_org_id() -> UUID:
    return uuid.uuid4()


@pytest.fixture()
def created_grant_ids(api_session):
    ids: list[int] = []
    yield ids
    for grant_id in ids:
        try:
            delete_permission_grant(api_session, grant_id=grant_id)
        except PDCNotFoundError:
            pass


def _changemaker_view_spec(*, changemaker_id: int, grantee_org_id: UUID) -> ChangemakerPermissionGrant:
    return ChangemakerPermissionGrant(
        changemaker_id=changemaker_id,
        grantee_type=PermissionGrantGranteeType.USER_GROUP,
        grantee_keycloak_organization_id=grantee_org_id,
        verbs=[PermissionGrantVerb.VIEW],
        scope=[
            PermissionGrantEntityType.PROPOSAL,
            PermissionGrantEntityType.PROPOSAL_FIELD_VALUE,
        ],
    )


def _changemaker_manage_spec(*, changemaker_id: int, grantee_org_id: UUID) -> ChangemakerPermissionGrant:
    return ChangemakerPermissionGrant(
        changemaker_id=changemaker_id,
        grantee_type=PermissionGrantGranteeType.USER_GROUP,
        grantee_keycloak_organization_id=grantee_org_id,
        verbs=[PermissionGrantVerb.MANAGE],
        scope=[PermissionGrantEntityType.ANY],
    )


def _funder_manage_spec(*, funder_short_code: str, grantee_org_id: UUID) -> FunderPermissionGrant:
    return FunderPermissionGrant(
        funder_short_code=funder_short_code,
        grantee_type=PermissionGrantGranteeType.USER_GROUP,
        grantee_keycloak_organization_id=grantee_org_id,
        verbs=[PermissionGrantVerb.MANAGE],
        scope=[PermissionGrantEntityType.ANY],
    )


def _proposal_view_spec(*, proposal_id: int, grantee_org_id: UUID) -> ProposalPermissionGrant:
    return ProposalPermissionGrant(
        proposal_id=proposal_id,
        grantee_type=PermissionGrantGranteeType.USER_GROUP,
        grantee_keycloak_organization_id=grantee_org_id,
        verbs=[PermissionGrantVerb.VIEW],
        scope=[
            PermissionGrantEntityType.PROPOSAL,
            PermissionGrantEntityType.PROPOSAL_FIELD_VALUE,
        ],
    )


class TestPermissionGrantsLifecycle:
    def test_create_get_update_delete_roundtrip(self, api_session, seeded_pdc_stack, grantee_org_id, created_grant_ids):
        spec = _changemaker_view_spec(
            changemaker_id=seeded_pdc_stack.changemaker.id,
            grantee_org_id=grantee_org_id,
        )

        created = create_permission_grant(api_session, spec=spec)
        created_grant_ids.append(created.id)

        assert isinstance(created, ChangemakerPermissionGrant)
        assert created.id is not None
        assert created.changemaker_id == seeded_pdc_stack.changemaker.id
        assert created.grantee_keycloak_organization_id == grantee_org_id
        assert created.verbs == [PermissionGrantVerb.VIEW]

        fetched = get_permission_grant(api_session, grant_id=created.id)
        assert fetched.id == created.id

        update_spec = _changemaker_view_spec(
            changemaker_id=seeded_pdc_stack.changemaker.id,
            grantee_org_id=grantee_org_id,
        )
        update_spec.verbs = [PermissionGrantVerb.VIEW, PermissionGrantVerb.EDIT]
        updated = update_permission_grant(api_session, grant_id=created.id, spec=update_spec)
        assert set(updated.verbs) == {PermissionGrantVerb.VIEW, PermissionGrantVerb.EDIT}

        delete_permission_grant(api_session, grant_id=created.id)
        created_grant_ids.remove(created.id)

        with pytest.raises(PDCNotFoundError):
            get_permission_grant(api_session, grant_id=created.id)

    def test_list_includes_created_grant(self, api_session, seeded_pdc_stack, grantee_org_id, created_grant_ids):
        spec = _changemaker_view_spec(
            changemaker_id=seeded_pdc_stack.changemaker.id,
            grantee_org_id=grantee_org_id,
        )
        created = create_permission_grant(api_session, spec=spec)
        created_grant_ids.append(created.id)

        bundle = list_permission_grants(api_session, count_per_page=200)

        assert any(entry.id == created.id for entry in bundle.entries)

    def test_authenticated_users_changemaker_grant_roundtrips(self, api_session, seeded_pdc_stack, created_grant_ids):
        spec = ChangemakerPermissionGrant(
            changemaker_id=seeded_pdc_stack.changemaker.id,
            grantee_type=PermissionGrantGranteeType.AUTHENTICATED_USERS,
            verbs=[PermissionGrantVerb.VIEW],
            scope=[
                PermissionGrantEntityType.PROPOSAL,
                PermissionGrantEntityType.PROPOSAL_FIELD_VALUE,
            ],
        )

        created = create_permission_grant(api_session, spec=spec)
        assert created.id is not None
        created_grant_ids.append(created.id)

        assert isinstance(created, ChangemakerPermissionGrant)
        assert created.grantee_type == PermissionGrantGranteeType.AUTHENTICATED_USERS
        assert created.grantee_user_keycloak_user_id is None
        assert created.grantee_keycloak_organization_id is None

        fetched = get_permission_grant(api_session, grant_id=created.id)
        assert fetched.grantee_type == PermissionGrantGranteeType.AUTHENTICATED_USERS
        assert fetched.grantee_user_keycloak_user_id is None
        assert fetched.grantee_keycloak_organization_id is None

    def test_proposal_context_grant_with_conditions(
        self, api_session, seeded_pdc_stack, grantee_org_id, created_grant_ids
    ):
        spec = ProposalPermissionGrant(
            proposal_id=seeded_pdc_stack.proposal.id,
            grantee_type=PermissionGrantGranteeType.USER_GROUP,
            grantee_keycloak_organization_id=grantee_org_id,
            verbs=[PermissionGrantVerb.VIEW],
            scope=[PermissionGrantEntityType.PROPOSAL_FIELD_VALUE],
            conditions=PermissionGrantConditions(
                proposal_field_value=PermissionGrantConditionRule(
                    property="baseFieldCategory",
                    operator="in",
                    value=[BaseFieldCategory.PROJECT],
                )
            ),
        )

        created = create_permission_grant(api_session, spec=spec)
        created_grant_ids.append(created.id)

        assert isinstance(created, ProposalPermissionGrant)
        assert created.proposal_id == seeded_pdc_stack.proposal.id
        assert created.conditions is not None
        assert created.conditions.proposal_field_value is not None
        assert created.conditions.proposal_field_value.value == [BaseFieldCategory.PROJECT]


class TestListFiltering:
    def test_changemaker_filter_scopes_results_server_side(self, api_session, seeded_pdc_stack, created_grant_ids):
        changemaker_b = seed_changemaker(api_session)

        match = create_permission_grant(
            api_session,
            spec=_changemaker_view_spec(changemaker_id=changemaker_b.id, grantee_org_id=uuid.uuid4()),
        )
        created_grant_ids.append(match.id)
        other_changemaker = create_permission_grant(
            api_session,
            spec=_changemaker_view_spec(changemaker_id=seeded_pdc_stack.changemaker.id, grantee_org_id=uuid.uuid4()),
        )
        created_grant_ids.append(other_changemaker.id)
        non_changemaker = create_permission_grant(
            api_session,
            spec=_funder_manage_spec(funder_short_code=seeded_pdc_stack.funder.short_code, grantee_org_id=uuid.uuid4()),
        )
        created_grant_ids.append(non_changemaker.id)

        bundle = list_permission_grants(api_session, changemaker=changemaker_b.id, count_per_page=200)

        returned_ids = {entry.id for entry in bundle.entries}
        assert match.id in returned_ids
        assert other_changemaker.id not in returned_ids
        assert non_changemaker.id not in returned_ids
        assert all(
            isinstance(entry, ChangemakerPermissionGrant) and entry.changemaker_id == changemaker_b.id
            for entry in bundle.entries
        )

    def test_funder_filter_scopes_results_server_side(self, api_session, seeded_pdc_stack, created_grant_ids):
        funder_b = seed_funder(api_session)

        match = create_permission_grant(
            api_session,
            spec=_funder_manage_spec(funder_short_code=funder_b.short_code, grantee_org_id=uuid.uuid4()),
        )
        created_grant_ids.append(match.id)
        other_funder = create_permission_grant(
            api_session,
            spec=_funder_manage_spec(funder_short_code=seeded_pdc_stack.funder.short_code, grantee_org_id=uuid.uuid4()),
        )
        created_grant_ids.append(other_funder.id)
        non_funder = create_permission_grant(
            api_session,
            spec=_changemaker_view_spec(changemaker_id=seeded_pdc_stack.changemaker.id, grantee_org_id=uuid.uuid4()),
        )
        created_grant_ids.append(non_funder.id)

        bundle = list_permission_grants(api_session, funder=funder_b.short_code, count_per_page=200)

        returned_ids = {entry.id for entry in bundle.entries}
        assert match.id in returned_ids
        assert other_funder.id not in returned_ids
        assert non_funder.id not in returned_ids
        assert all(
            isinstance(entry, FunderPermissionGrant) and entry.funder_short_code == funder_b.short_code
            for entry in bundle.entries
        )

    def test_proposal_filter_scopes_results_server_side(self, api_session, seeded_pdc_stack, created_grant_ids):
        proposal_b = seed_proposal(api_session)

        match = create_permission_grant(
            api_session,
            spec=_proposal_view_spec(proposal_id=proposal_b.id, grantee_org_id=uuid.uuid4()),
        )
        created_grant_ids.append(match.id)
        other_proposal = create_permission_grant(
            api_session,
            spec=_proposal_view_spec(proposal_id=seeded_pdc_stack.proposal.id, grantee_org_id=uuid.uuid4()),
        )
        created_grant_ids.append(other_proposal.id)
        non_proposal = create_permission_grant(
            api_session,
            spec=_changemaker_view_spec(changemaker_id=seeded_pdc_stack.changemaker.id, grantee_org_id=uuid.uuid4()),
        )
        created_grant_ids.append(non_proposal.id)

        bundle = list_permission_grants(api_session, proposal=proposal_b.id, count_per_page=200)

        returned_ids = {entry.id for entry in bundle.entries}
        assert match.id in returned_ids
        assert other_proposal.id not in returned_ids
        assert non_proposal.id not in returned_ids
        assert all(
            isinstance(entry, ProposalPermissionGrant) and entry.proposal_id == proposal_b.id
            for entry in bundle.entries
        )

    def test_verb_filter_scopes_results_server_side(self, api_session, seeded_pdc_stack, created_grant_ids):
        changemaker_id = seeded_pdc_stack.changemaker.id
        manage_grant = create_permission_grant(
            api_session,
            spec=_changemaker_manage_spec(changemaker_id=changemaker_id, grantee_org_id=uuid.uuid4()),
        )
        created_grant_ids.append(manage_grant.id)
        view_grant = create_permission_grant(
            api_session,
            spec=_changemaker_view_spec(changemaker_id=changemaker_id, grantee_org_id=uuid.uuid4()),
        )
        created_grant_ids.append(view_grant.id)

        bundle = list_permission_grants(api_session, verb=PermissionGrantVerb.MANAGE, count_per_page=200)

        returned_ids = {entry.id for entry in bundle.entries}
        assert manage_grant.id in returned_ids
        assert view_grant.id not in returned_ids
        assert all(PermissionGrantVerb.MANAGE in entry.verbs for entry in bundle.entries)

    def test_grantee_type_filter_scopes_results_server_side(self, api_session, seeded_pdc_stack, created_grant_ids):
        changemaker_id = seeded_pdc_stack.changemaker.id
        authenticated_users_grant = create_permission_grant(
            api_session,
            spec=ChangemakerPermissionGrant(
                changemaker_id=changemaker_id,
                grantee_type=PermissionGrantGranteeType.AUTHENTICATED_USERS,
                verbs=[PermissionGrantVerb.VIEW],
                scope=[
                    PermissionGrantEntityType.PROPOSAL,
                    PermissionGrantEntityType.PROPOSAL_FIELD_VALUE,
                ],
            ),
        )
        created_grant_ids.append(authenticated_users_grant.id)
        user_group_grant = create_permission_grant(
            api_session,
            spec=_changemaker_view_spec(changemaker_id=changemaker_id, grantee_org_id=uuid.uuid4()),
        )
        created_grant_ids.append(user_group_grant.id)

        bundle = list_permission_grants(
            api_session, grantee_type=PermissionGrantGranteeType.AUTHENTICATED_USERS, count_per_page=200
        )

        returned_ids = {entry.id for entry in bundle.entries}
        assert authenticated_users_grant.id in returned_ids
        assert user_group_grant.id not in returned_ids
        assert all(entry.grantee_type == PermissionGrantGranteeType.AUTHENTICATED_USERS for entry in bundle.entries)


class TestPermissionGrantsErrors:
    def test_get_nonexistent_raises_not_found(self, api_session):
        with pytest.raises(PDCNotFoundError):
            get_permission_grant(api_session, grant_id=999_999_999)

    def test_delete_nonexistent_raises_not_found(self, api_session):
        with pytest.raises(PDCNotFoundError):
            delete_permission_grant(api_session, grant_id=999_999_999)
