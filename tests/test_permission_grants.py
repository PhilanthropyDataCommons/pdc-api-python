from typing import Any
from uuid import UUID

import pytest

from pdc_api.permission_grants import (
    ApplicationFormFieldPermissionGrant,
    ApplicationFormPermissionGrant,
    BulkUploadPermissionGrant,
    ChangemakerFieldValuePermissionGrant,
    ChangemakerPermissionGrant,
    DataProviderPermissionGrant,
    DefaultPermissionGrant,
    FunderPermissionGrant,
    InitiativeFieldValuePermissionGrant,
    InitiativePermissionGrant,
    OpportunityPermissionGrant,
    PermissionGrantBundle,
    PermissionGrantEntityType,
    PermissionGrantGranteeType,
    PermissionGrantVerb,
    ProposalFieldValuePermissionGrant,
    ProposalPermissionGrant,
    ProposalVersionPermissionGrant,
    SourcePermissionGrant,
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

EXPECTED_GRANTEE_KEY = {
    PermissionGrantGranteeType.USER: "grantee_user_keycloak_user_id",
    PermissionGrantGranteeType.USER_GROUP: "grantee_keycloak_organization_id",
    PermissionGrantGranteeType.AUTHENTICATED_USERS: None,
    PermissionGrantGranteeType.ALL_FUNDERS: None,
}


def _required_keys(grantee_type: PermissionGrantGranteeType) -> set[str]:
    key = EXPECTED_GRANTEE_KEY[grantee_type]
    return {key} if key else set()


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
    def test_every_grantee_type_has_an_expected_key(self):
        assert set(PermissionGrantGranteeType) - set(EXPECTED_GRANTEE_KEY) == set()

    @pytest.mark.parametrize("grantee_type", list(EXPECTED_GRANTEE_KEY))
    def test_accepts_the_keys_its_type_requires(self, grantee_type):
        grant = _grant_with_keys(grantee_type, _required_keys(grantee_type))

        assert {key for key in GRANTEE_KEY_VALUES if getattr(grant, key)} == _required_keys(grantee_type)

    @pytest.mark.parametrize(
        ("grantee_type", "key"), [(grantee_type, key) for grantee_type, key in EXPECTED_GRANTEE_KEY.items() if key]
    )
    def test_requires_the_key_its_type_names(self, grantee_type, key):
        with pytest.raises(ValueError, match=f"{key} is required"):
            _grant_with_keys(grantee_type, set())

    @pytest.mark.parametrize(
        ("grantee_type", "key"),
        [
            (grantee_type, key)
            for grantee_type in EXPECTED_GRANTEE_KEY
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


EXPECTED_VARIANT = {
    PermissionGrantEntityType.FUNDER: (FunderPermissionGrant, {"funderShortCode": "acme"}),
    PermissionGrantEntityType.CHANGEMAKER: (ChangemakerPermissionGrant, {"changemakerId": 9}),
    PermissionGrantEntityType.DATA_PROVIDER: (DataProviderPermissionGrant, {"dataProviderShortCode": "acme"}),
    PermissionGrantEntityType.OPPORTUNITY: (OpportunityPermissionGrant, {"opportunityId": 1}),
    PermissionGrantEntityType.PROPOSAL: (ProposalPermissionGrant, {"proposalId": 1}),
    PermissionGrantEntityType.PROPOSAL_VERSION: (ProposalVersionPermissionGrant, {"proposalVersionId": 1}),
    PermissionGrantEntityType.APPLICATION_FORM: (ApplicationFormPermissionGrant, {"applicationFormId": 1}),
    PermissionGrantEntityType.APPLICATION_FORM_FIELD: (
        ApplicationFormFieldPermissionGrant,
        {"applicationFormFieldId": 1},
    ),
    PermissionGrantEntityType.PROPOSAL_FIELD_VALUE: (ProposalFieldValuePermissionGrant, {"proposalFieldValueId": 1}),
    PermissionGrantEntityType.SOURCE: (SourcePermissionGrant, {"sourceId": 1}),
    PermissionGrantEntityType.BULK_UPLOAD: (BulkUploadPermissionGrant, {"bulkUploadTaskId": 1}),
    PermissionGrantEntityType.CHANGEMAKER_FIELD_VALUE: (
        ChangemakerFieldValuePermissionGrant,
        {"changemakerFieldValueId": 1},
    ),
    PermissionGrantEntityType.TERMINOLOGY_SET: (TerminologySetPermissionGrant, {"terminologySetId": 3}),
    PermissionGrantEntityType.INITIATIVE: (InitiativePermissionGrant, {"initiativeId": 42}),
    PermissionGrantEntityType.INITIATIVE_FIELD_VALUE: (
        InitiativeFieldValuePermissionGrant,
        {"initiativeFieldValueId": 7},
    ),
    PermissionGrantEntityType.ANY: None,
}


class TestVariantDiscrimination:
    def test_every_context_entity_type_has_an_expected_variant(self):
        assert set(PermissionGrantEntityType) - set(EXPECTED_VARIANT) == set()

    @pytest.mark.parametrize(
        ("context_entity_type", "variant", "context"),
        [
            (context_entity_type, *expected)
            for context_entity_type, expected in EXPECTED_VARIANT.items()
            if expected is not None
        ],
    )
    def test_parses_each_context_into_its_variant(
        self, session, add_page_response, context_entity_type, variant, context
    ):
        payload = _changemaker_grant_payload(grant_id=1, changemaker_id=9, grantee_org_id=ORG_UUID)
        del payload["changemakerId"]
        add_page_response(
            PermissionGrantBundle, payload=bundle([{**payload, "contextEntityType": context_entity_type, **context}])
        )

        [grant] = list_permission_grants(session).entries

        assert isinstance(grant, variant)

    def test_rejects_any_as_a_grant_context(self, session, add_page_response):
        payload = _changemaker_grant_payload(grant_id=1, changemaker_id=9, grantee_org_id=ORG_UUID)
        add_page_response(PermissionGrantBundle, payload=bundle([{**payload, "contextEntityType": "any"}]))

        with pytest.raises(ValueError):
            list_permission_grants(session)

    def test_initiative_field_value_condition_round_trips(self, session, add_page_response):
        payload = {**_changemaker_grant_payload(grant_id=1, changemaker_id=9, grantee_org_id=ORG_UUID)}
        payload["scope"] = ["initiativeFieldValue"]
        payload["conditions"] = {
            "initiativeFieldValue": {"property": "baseFieldCategory", "operator": "in", "value": ["project"]}
        }
        add_page_response(PermissionGrantBundle, payload=bundle([payload]))

        [grant] = list_permission_grants(session).entries

        assert _grant_to_payload(grant)["conditions"] == payload["conditions"]
