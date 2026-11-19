from typing import Any
from uuid import UUID

import pytest

from pdc_api.permission_grants import (
    ChangemakerPermissionGrant,
    DefaultPermissionGrant,
    InitiativeFieldValuePermissionGrant,
    InitiativePermissionGrant,
    PermissionGrantBundle,
    PermissionGrantEntityType,
    PermissionGrantGranteeType,
    PermissionGrantVerb,
    TerminologySetPermissionGrant,
    _grant_to_payload,
    list_permission_grants,
)
from pdc_api.testing import bundle

ORG_UUID = UUID("00000000-0000-0000-0000-000000000001")
USER_UUID = UUID("00000000-0000-0000-0000-000000000002")


def _changemaker_grant_payload(*, grant_id: int, changemaker_id: int, grantee_org_id: UUID) -> dict[str, Any]:
    return {
        "id": grant_id,
        "contextEntityType": "changemaker",
        "changemakerId": changemaker_id,
        "granteeType": "userGroup",
        "granteeKeycloakOrganizationId": str(grantee_org_id),
        "verbs": ["create"],
        "scope": ["changemakerFieldValue"],
        "conditions": None,
        "createdAt": "2026-01-01T00:00:00Z",
        "createdBy": "00000000-0000-0000-0000-000000000009",
    }


class TestGranteeKeyValidator:
    def test_user_grantee_requires_user_uuid(self):
        with pytest.raises(ValueError, match="grantee_user_keycloak_user_id is required"):
            ChangemakerPermissionGrant(
                changemaker_id=7,
                grantee_type=PermissionGrantGranteeType.USER,
                grantee_keycloak_organization_id=ORG_UUID,
                verbs=[PermissionGrantVerb.VIEW],
                scope=[PermissionGrantEntityType.PROPOSAL],
            )

    def test_user_group_grantee_rejects_user_uuid(self):
        with pytest.raises(ValueError, match="grantee_user_keycloak_user_id must not be set"):
            ChangemakerPermissionGrant(
                changemaker_id=7,
                grantee_type=PermissionGrantGranteeType.USER_GROUP,
                grantee_keycloak_organization_id=ORG_UUID,
                grantee_user_keycloak_user_id=USER_UUID,
                verbs=[PermissionGrantVerb.VIEW],
                scope=[PermissionGrantEntityType.PROPOSAL],
            )

    def test_authenticated_users_grantee_allows_both_keys_null(self):
        grant = ChangemakerPermissionGrant(
            changemaker_id=7,
            grantee_type=PermissionGrantGranteeType.AUTHENTICATED_USERS,
            verbs=[PermissionGrantVerb.VIEW],
            scope=[PermissionGrantEntityType.PROPOSAL],
        )
        assert grant.grantee_user_keycloak_user_id is None
        assert grant.grantee_keycloak_organization_id is None

    def test_authenticated_users_grantee_rejects_org_uuid(self):
        with pytest.raises(ValueError, match="grantee_keycloak_organization_id must not be set"):
            ChangemakerPermissionGrant(
                changemaker_id=7,
                grantee_type=PermissionGrantGranteeType.AUTHENTICATED_USERS,
                grantee_keycloak_organization_id=ORG_UUID,
                verbs=[PermissionGrantVerb.VIEW],
                scope=[PermissionGrantEntityType.PROPOSAL],
            )

    def test_authenticated_users_grantee_rejects_user_uuid(self):
        with pytest.raises(ValueError, match="grantee_user_keycloak_user_id must not be set"):
            ChangemakerPermissionGrant(
                changemaker_id=7,
                grantee_type=PermissionGrantGranteeType.AUTHENTICATED_USERS,
                grantee_user_keycloak_user_id=USER_UUID,
                verbs=[PermissionGrantVerb.VIEW],
                scope=[PermissionGrantEntityType.PROPOSAL],
            )


class TestDefaultPermissionGrantContext:
    def test_rejects_any_context_entity_type(self):
        with pytest.raises(ValueError, match="context_entity_type cannot be 'any'"):
            DefaultPermissionGrant(
                context_entity_type=PermissionGrantEntityType.ANY,
                grantee_type=PermissionGrantGranteeType.AUTHENTICATED_USERS,
                verbs=[PermissionGrantVerb.VIEW],
                scope=[PermissionGrantEntityType.PROPOSAL],
            )

    def test_allows_any_in_scope(self):
        grant = DefaultPermissionGrant(
            context_entity_type=PermissionGrantEntityType.CHANGEMAKER,
            grantee_type=PermissionGrantGranteeType.AUTHENTICATED_USERS,
            verbs=[PermissionGrantVerb.VIEW],
            scope=[PermissionGrantEntityType.ANY],
        )
        assert grant.scope == [PermissionGrantEntityType.ANY]


class TestListFilters:
    def test_filters_become_query_params(self, session, add_page_response):
        add_page_response(
            PermissionGrantBundle,
            payload=bundle([_changemaker_grant_payload(grant_id=1, changemaker_id=9, grantee_org_id=ORG_UUID)]),
            extra_params={
                "changemaker": 9,
                "funder": "acme-foundation",
                "proposal": 7,
                "granteeType": "userGroup",
                "verb": "manage",
            },
        )

        result = list_permission_grants(
            session,
            changemaker_id=9,
            funder_short_code="acme-foundation",
            proposal_id=7,
            grantee_type=PermissionGrantGranteeType.USER_GROUP,
            verb=PermissionGrantVerb.MANAGE,
        )

        assert [entry.id for entry in result.entries] == [1]

    def test_no_filters_sends_no_filter_params(self, session, add_page_response):
        # Registered without extra_params: matches only a bare _page/_count query.
        add_page_response(PermissionGrantBundle, payload=bundle([]))

        result = list_permission_grants(session)

        assert result.entries == []


class TestVariantDiscrimination:
    @pytest.mark.parametrize(
        ("context", "variant"),
        [
            ({"contextEntityType": "initiative", "initiativeId": 42}, InitiativePermissionGrant),
            (
                {"contextEntityType": "initiativeFieldValue", "initiativeFieldValueId": 7},
                InitiativeFieldValuePermissionGrant,
            ),
            ({"contextEntityType": "terminologySet", "terminologySetId": 3}, TerminologySetPermissionGrant),
        ],
    )
    def test_parses_initiative_and_terminology_set_grants(self, session, add_page_response, context, variant):
        payload = {**_changemaker_grant_payload(grant_id=1, changemaker_id=9, grantee_org_id=ORG_UUID), **context}
        del payload["changemakerId"]
        add_page_response(PermissionGrantBundle, payload=bundle([payload]))

        [grant] = list_permission_grants(session).entries

        assert isinstance(grant, variant)

    def test_initiative_field_value_condition_round_trips(self, session, add_page_response):
        payload = {**_changemaker_grant_payload(grant_id=1, changemaker_id=9, grantee_org_id=ORG_UUID)}
        payload["scope"] = ["initiativeFieldValue"]
        payload["conditions"] = {
            "initiativeFieldValue": {"property": "baseFieldCategory", "operator": "in", "value": ["project"]}
        }
        add_page_response(PermissionGrantBundle, payload=bundle([payload]))

        [grant] = list_permission_grants(session).entries

        assert _grant_to_payload(grant)["conditions"] == payload["conditions"]
