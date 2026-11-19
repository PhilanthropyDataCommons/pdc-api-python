from datetime import datetime
from typing import Annotated, Any, ClassVar, Literal, Self
from uuid import UUID

from pydantic import Field, TypeAdapter, field_validator, model_validator

from pdc_api.client import get_bundle_page
from pdc_api.models import (
    BaseFieldCategory,
    BaseSchema,
    PermissionGrantEntityType,
    PermissionGrantGranteeType,
    PermissionGrantVerb,
)
from pdc_api.transport import APISession

_ENDPOINT = "permissionGrants"
_DEFAULT_ENDPOINT = "defaultPermissionGrants"

_DEFAULT_PAGE_SIZE = 50


class PermissionGrantConditionRule(BaseSchema):
    property: Literal["baseFieldCategory"]
    operator: Literal["in"]
    value: list[BaseFieldCategory] = Field(min_length=1)


class PermissionGrantConditions(BaseSchema):
    proposal_field_value: PermissionGrantConditionRule | None = Field(default=None, alias="proposalFieldValue")
    initiative_field_value: PermissionGrantConditionRule | None = Field(default=None, alias="initiativeFieldValue")


class _PermissionGrantBase(BaseSchema):
    id: int | None = None
    grantee_type: PermissionGrantGranteeType = Field(alias="granteeType")
    grantee_user_keycloak_user_id: UUID | None = Field(default=None, alias="granteeUserKeycloakUserId")
    grantee_keycloak_organization_id: UUID | None = Field(default=None, alias="granteeKeycloakOrganizationId")
    verbs: list[PermissionGrantVerb] = Field(min_length=1)
    scope: list[PermissionGrantEntityType] = Field(min_length=1)
    conditions: PermissionGrantConditions | None = None
    created_by: UUID | None = Field(default=None, alias="createdBy")
    created_at: datetime | None = Field(default=None, alias="createdAt")

    @model_validator(mode="after")
    def _check_grantee_keys_match_type(self) -> Self:
        if self.grantee_type == PermissionGrantGranteeType.USER:
            if self.grantee_user_keycloak_user_id is None:
                raise ValueError("grantee_user_keycloak_user_id is required when grantee_type is 'user'")
            if self.grantee_keycloak_organization_id is not None:
                raise ValueError("grantee_keycloak_organization_id must not be set when grantee_type is 'user'")
        elif self.grantee_type == PermissionGrantGranteeType.USER_GROUP:
            if self.grantee_keycloak_organization_id is None:
                raise ValueError("grantee_keycloak_organization_id is required when grantee_type is 'userGroup'")
            if self.grantee_user_keycloak_user_id is not None:
                raise ValueError("grantee_user_keycloak_user_id must not be set when grantee_type is 'userGroup'")
        elif self.grantee_type == PermissionGrantGranteeType.AUTHENTICATED_USERS:
            if self.grantee_user_keycloak_user_id is not None:
                raise ValueError(
                    "grantee_user_keycloak_user_id must not be set when grantee_type is 'authenticatedUsers'"
                )
            if self.grantee_keycloak_organization_id is not None:
                raise ValueError(
                    "grantee_keycloak_organization_id must not be set when grantee_type is 'authenticatedUsers'"
                )
        else:
            raise ValueError(f"Unknown grantee_type: {self.grantee_type!r}")
        return self


class ChangemakerPermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.CHANGEMAKER] = Field(
        default=PermissionGrantEntityType.CHANGEMAKER, alias="contextEntityType"
    )
    changemaker_id: int = Field(alias="changemakerId")


class FunderPermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.FUNDER] = Field(
        default=PermissionGrantEntityType.FUNDER, alias="contextEntityType"
    )
    funder_short_code: str = Field(alias="funderShortCode")


class DataProviderPermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.DATA_PROVIDER] = Field(
        default=PermissionGrantEntityType.DATA_PROVIDER, alias="contextEntityType"
    )
    data_provider_short_code: str = Field(alias="dataProviderShortCode")


class OpportunityPermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.OPPORTUNITY] = Field(
        default=PermissionGrantEntityType.OPPORTUNITY, alias="contextEntityType"
    )
    opportunity_id: int = Field(alias="opportunityId")


class ProposalPermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.PROPOSAL] = Field(
        default=PermissionGrantEntityType.PROPOSAL, alias="contextEntityType"
    )
    proposal_id: int = Field(alias="proposalId")


class ProposalVersionPermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.PROPOSAL_VERSION] = Field(
        default=PermissionGrantEntityType.PROPOSAL_VERSION, alias="contextEntityType"
    )
    proposal_version_id: int = Field(alias="proposalVersionId")


class ApplicationFormPermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.APPLICATION_FORM] = Field(
        default=PermissionGrantEntityType.APPLICATION_FORM, alias="contextEntityType"
    )
    application_form_id: int = Field(alias="applicationFormId")


class ApplicationFormFieldPermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.APPLICATION_FORM_FIELD] = Field(
        default=PermissionGrantEntityType.APPLICATION_FORM_FIELD, alias="contextEntityType"
    )
    application_form_field_id: int = Field(alias="applicationFormFieldId")


class ProposalFieldValuePermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.PROPOSAL_FIELD_VALUE] = Field(
        default=PermissionGrantEntityType.PROPOSAL_FIELD_VALUE, alias="contextEntityType"
    )
    proposal_field_value_id: int = Field(alias="proposalFieldValueId")


class SourcePermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.SOURCE] = Field(
        default=PermissionGrantEntityType.SOURCE, alias="contextEntityType"
    )
    source_id: int = Field(alias="sourceId")


class BulkUploadPermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.BULK_UPLOAD] = Field(
        default=PermissionGrantEntityType.BULK_UPLOAD, alias="contextEntityType"
    )
    bulk_upload_task_id: int = Field(alias="bulkUploadTaskId")


class ChangemakerFieldValuePermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.CHANGEMAKER_FIELD_VALUE] = Field(
        default=PermissionGrantEntityType.CHANGEMAKER_FIELD_VALUE, alias="contextEntityType"
    )
    changemaker_field_value_id: int = Field(alias="changemakerFieldValueId")


class TerminologySetPermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.TERMINOLOGY_SET] = Field(
        default=PermissionGrantEntityType.TERMINOLOGY_SET, alias="contextEntityType"
    )
    terminology_set_id: int = Field(alias="terminologySetId")


class InitiativePermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.INITIATIVE] = Field(
        default=PermissionGrantEntityType.INITIATIVE, alias="contextEntityType"
    )
    initiative_id: int = Field(alias="initiativeId")


class InitiativeFieldValuePermissionGrant(_PermissionGrantBase):
    context_entity_type: Literal[PermissionGrantEntityType.INITIATIVE_FIELD_VALUE] = Field(
        default=PermissionGrantEntityType.INITIATIVE_FIELD_VALUE, alias="contextEntityType"
    )
    initiative_field_value_id: int = Field(alias="initiativeFieldValueId")


PermissionGrant = Annotated[
    ChangemakerPermissionGrant
    | FunderPermissionGrant
    | DataProviderPermissionGrant
    | OpportunityPermissionGrant
    | ProposalPermissionGrant
    | ProposalVersionPermissionGrant
    | ApplicationFormPermissionGrant
    | ApplicationFormFieldPermissionGrant
    | ProposalFieldValuePermissionGrant
    | SourcePermissionGrant
    | BulkUploadPermissionGrant
    | ChangemakerFieldValuePermissionGrant
    | TerminologySetPermissionGrant
    | InitiativePermissionGrant
    | InitiativeFieldValuePermissionGrant,
    Field(discriminator="context_entity_type"),
]

_PERMISSION_GRANT_ADAPTER: TypeAdapter[PermissionGrant] = TypeAdapter(PermissionGrant)


class PermissionGrantBundle(BaseSchema):
    pdc_endpoint: ClassVar[str] = _ENDPOINT
    default_page_size: ClassVar[int] = _DEFAULT_PAGE_SIZE
    entries: list[PermissionGrant]
    total: int


class DefaultPermissionGrant(_PermissionGrantBase):
    context_entity_type: PermissionGrantEntityType = Field(alias="contextEntityType")

    @field_validator("context_entity_type")
    @classmethod
    def _reject_any_context(cls, value: PermissionGrantEntityType) -> PermissionGrantEntityType:
        # PDC accepts "any" in scope but not as a default's context.
        if value == PermissionGrantEntityType.ANY:
            raise ValueError("context_entity_type cannot be 'any'")
        return value


class DefaultPermissionGrantBundle(BaseSchema):
    pdc_endpoint: ClassVar[str] = _DEFAULT_ENDPOINT
    default_page_size: ClassVar[int] = _DEFAULT_PAGE_SIZE
    entries: list[DefaultPermissionGrant]
    total: int


def _validate_grant(payload: dict[str, Any]) -> PermissionGrant:
    return _PERMISSION_GRANT_ADAPTER.validate_python(payload)


def _grant_to_payload(grant: PermissionGrant | DefaultPermissionGrant) -> dict[str, Any]:
    # PDC rejects server-managed fields and the unset grantee key in write bodies.
    return grant.model_dump(mode="json", by_alias=True, exclude={"id", "created_by", "created_at"}, exclude_none=True)


def list_permission_grants(
    session: APISession,
    *,
    page: int = 1,
    count_per_page: int | None = None,
    changemaker_id: int | None = None,
    funder_short_code: str | None = None,
    proposal_id: int | None = None,
    grantee_type: PermissionGrantGranteeType | None = None,
    verb: PermissionGrantVerb | None = None,
) -> PermissionGrantBundle:
    extra_params: dict[str, Any] = {}
    if changemaker_id is not None:
        extra_params["changemaker"] = changemaker_id
    if funder_short_code is not None:
        extra_params["funder"] = funder_short_code
    if proposal_id is not None:
        extra_params["proposal"] = proposal_id
    if grantee_type is not None:
        extra_params["granteeType"] = grantee_type.value
    if verb is not None:
        extra_params["verb"] = verb.value
    return get_bundle_page(
        session,
        PermissionGrantBundle,
        page=page,
        count_per_page=count_per_page,
        extra_params=extra_params or None,
    )


def get_permission_grant(session: APISession, *, grant_id: int) -> PermissionGrant:
    response = session.get(f"{_ENDPOINT}/{grant_id}")
    return _validate_grant(response.json())


def create_permission_grant(session: APISession, *, grant: PermissionGrant) -> PermissionGrant:
    response = session.post(_ENDPOINT, json=_grant_to_payload(grant))
    return _validate_grant(response.json())


def update_permission_grant(session: APISession, *, grant_id: int, grant: PermissionGrant) -> PermissionGrant:
    response = session.put(f"{_ENDPOINT}/{grant_id}", json=_grant_to_payload(grant))
    return _validate_grant(response.json())


def delete_permission_grant(session: APISession, *, grant_id: int) -> None:
    session.delete(f"{_ENDPOINT}/{grant_id}")


def list_default_permission_grants(
    session: APISession, *, page: int = 1, count_per_page: int | None = None
) -> DefaultPermissionGrantBundle:
    return get_bundle_page(session, DefaultPermissionGrantBundle, page=page, count_per_page=count_per_page)


def get_default_permission_grant(session: APISession, *, grant_id: int) -> DefaultPermissionGrant:
    response = session.get(f"{_DEFAULT_ENDPOINT}/{grant_id}")
    return DefaultPermissionGrant.model_validate(response.json())


def create_default_permission_grant(session: APISession, *, grant: DefaultPermissionGrant) -> DefaultPermissionGrant:
    response = session.post(_DEFAULT_ENDPOINT, json=_grant_to_payload(grant))
    return DefaultPermissionGrant.model_validate(response.json())


def update_default_permission_grant(
    session: APISession, *, grant_id: int, grant: DefaultPermissionGrant
) -> DefaultPermissionGrant:
    response = session.put(f"{_DEFAULT_ENDPOINT}/{grant_id}", json=_grant_to_payload(grant))
    return DefaultPermissionGrant.model_validate(response.json())


def delete_default_permission_grant(session: APISession, *, grant_id: int) -> None:
    session.delete(f"{_DEFAULT_ENDPOINT}/{grant_id}")
