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


GRANTEE_KEY_VALUES = {"grantee_user_keycloak_user_id": USER_UUID, "grantee_keycloak_organization_id": ORG_UUID}

KEYED_GRANTEE_TYPES = {
    PermissionGrantGranteeType.USER: "grantee_user_keycloak_user_id",
    PermissionGrantGranteeType.USER_GROUP: "grantee_keycloak_organization_id",
}


def _required_keys(grantee_type: PermissionGrantGranteeType) -> set[str]:
    return {KEYED_GRANTEE_TYPES[grantee_type]} if grantee_type in KEYED_GRANTEE_TYPES else set()


def _grant_with_keys(grantee_type: PermissionGrantGranteeType, keys: set[str]) -> ChangemakerPermissionGrant:
    return ChangemakerPermissionGrant.model_validate(
        {
            "changemaker_id": 7,
            "grantee_type": grantee_type,
            "verbs": [PermissionGrantVerb.VIEW],
            "scope": [PermissionGrantEntityType.PROPOSAL],
            **{key: GRANTEE_KEY_VALUES[key] for key in keys},
        }
    )


class TestGranteeKeyValidator:
    @pytest.mark.parametrize("grantee_type", list(PermissionGrantGranteeType))
    def test_accepts_the_keys_its_type_requires(self, grantee_type):
        grant = _grant_with_keys(grantee_type, _required_keys(grantee_type))

        assert {key for key in GRANTEE_KEY_VALUES if getattr(grant, key)} == _required_keys(grantee_type)

    @pytest.mark.parametrize(("grantee_type", "key"), list(KEYED_GRANTEE_TYPES.items()))
    def test_requires_the_key_its_type_names(self, grantee_type, key):
        with pytest.raises(ValueError, match=f"{key} is required"):
            _grant_with_keys(grantee_type, set())

    @pytest.mark.parametrize(
        ("grantee_type", "key"),
        [
            (grantee_type, key)
            for grantee_type in PermissionGrantGranteeType
            for key in GRANTEE_KEY_VALUES
            if key not in _required_keys(grantee_type)
        ],
    )
    def test_rejects_keys_its_type_does_not_take(self, grantee_type, key):
        with pytest.raises(ValueError, match=f"{key} must not be set"):
            _grant_with_keys(grantee_type, _required_keys(grantee_type) | {key})


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
