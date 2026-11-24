from typing import Any
from uuid import UUID

import responses

from pdc_api.client import PageableBundle

CREATED_AT = "2026-01-01T00:00:00Z"
CREATED_BY = "00000000-0000-0000-0000-000000000009"


def changemaker_payload(
    *, id: int = 1, name: str = "Acme", keycloak_org_id: str | UUID | None = None, tax_id: str = "12-3456789"
) -> dict[str, Any]:
    return {
        "id": id,
        "taxId": tax_id,
        "name": name,
        "keycloakOrganizationId": keycloak_org_id,
        "createdAt": CREATED_AT,
        "createdBy": CREATED_BY,
        "fields": [],
        "fiscalSponsors": [],
        "permissions": {},
    }


def funder_payload(
    *,
    short_code: str = "acme",
    name: str = "Acme Foundation",
    keycloak_org_id: str | UUID | None = None,
    is_collaborative: bool = False,
) -> dict[str, Any]:
    return {
        "shortCode": short_code,
        "name": name,
        "keycloakOrganizationId": keycloak_org_id,
        "isCollaborative": is_collaborative,
        "createdAt": CREATED_AT,
        "createdBy": CREATED_BY,
        "permissions": {},
    }


def data_provider_payload(
    *, short_code: str = "pdw", name: str = "Philanthropy Data Warehouse", keycloak_org_id: str | UUID | None = None
) -> dict[str, Any]:
    return {
        "shortCode": short_code,
        "name": name,
        "keycloakOrganizationId": keycloak_org_id,
        "createdAt": CREATED_AT,
        "createdBy": CREATED_BY,
    }


def base_field_payload(
    short_code: str = "field", *, data_type: str = "string", category: str = "uncategorized"
) -> dict[str, Any]:
    return {
        "shortCode": short_code,
        "label": short_code,
        "category": category,
        "dataType": data_type,
        "description": "",
        "localizations": {},
        "valueRelevanceHours": None,
        "sensitivityClassification": "public",
        "createdAt": CREATED_AT,
    }


def proposal_payload(*, id: int = 100, opportunity_id: int = 5, external_id: str = "ext-1") -> dict[str, Any]:
    return {
        "id": id,
        "opportunityId": opportunity_id,
        "externalId": external_id,
        "versions": [],
        "changemakers": [],
        "createdAt": CREATED_AT,
        "createdBy": CREATED_BY,
    }


def initiative_payload(*, id: int = 1, changemaker_id: int = 10, title: str = "Summer meals") -> dict[str, Any]:
    return {
        "id": id,
        "changemakerId": changemaker_id,
        "title": title,
        "createdAt": CREATED_AT,
        "createdBy": CREATED_BY,
    }


def initiative_field_value_payload(
    *,
    id: int = 1,
    initiative_id: int = 1,
    short_code: str = "field",
    value: str = "",
    created_at: str = CREATED_AT,
    data_type: str = "string",
) -> dict[str, Any]:
    return {
        "id": id,
        "initiativeId": initiative_id,
        "baseFieldShortCode": short_code,
        "baseField": base_field_payload(short_code, data_type=data_type, category="project"),
        "sourceId": 1,
        "source": source_payload(),
        "value": value,
        "file": None,
        "goodAsOf": None,
        "isValid": True,
        "createdAt": created_at,
        "createdBy": CREATED_BY,
    }


def changemaker_proposal_payload(*, id: int = 1, changemaker_id: int = 10, proposal_id: int = 100) -> dict[str, Any]:
    return {
        "id": id,
        "changemakerId": changemaker_id,
        "changemaker": changemaker_payload(id=changemaker_id),
        "proposalId": proposal_id,
        "proposal": proposal_payload(id=proposal_id),
        "createdAt": CREATED_AT,
    }


def user_payload(
    *, keycloak_user_id: str | UUID, keycloak_user_name: str | None = "Ada Lovelace", disabled_at: str | None = None
) -> dict[str, Any]:
    return {
        "keycloakUserId": keycloak_user_id,
        "keycloakUserName": keycloak_user_name,
        "createdAt": CREATED_AT,
        "syncedFromKeycloakAt": CREATED_AT,
        "disabledAt": disabled_at,
    }


def organization_payload(
    *,
    keycloak_organization_id: str | UUID = "00000000-0000-0000-0000-0000000000a1",
    keycloak_organization_name: str | None = "Acme",
    disabled_at: str | None = None,
    changemaker: dict[str, Any] | None = None,
    funder: dict[str, Any] | None = None,
    data_provider: dict[str, Any] | None = None,
    members: list[dict[str, Any]] | None = None,
    former_members: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "keycloakOrganizationId": keycloak_organization_id,
        "keycloakOrganizationName": keycloak_organization_name,
        "disabledAt": disabled_at,
        "changemaker": changemaker,
        "funder": funder,
        "dataProvider": data_provider,
        "members": members,
        "formerMembers": former_members,
    }


def application_form_payload(*, id: int = 7, version: int = 1, opportunity_id: int = 5) -> dict[str, Any]:
    return {
        "id": id,
        "version": version,
        "opportunityId": opportunity_id,
        "name": f"Application form {id}",
        "fields": [],
        "createdAt": CREATED_AT,
    }


def source_payload(*, id: int = 1, label: str = "src") -> dict[str, Any]:
    return {"id": id, "label": label, "createdAt": CREATED_AT}


def proposal_version_payload(*, id: int = 1, proposal_id: int = 100, version: int = 1) -> dict[str, Any]:
    return {
        "id": id,
        "proposalId": proposal_id,
        "sourceId": 1,
        "source": source_payload(),
        "applicationFormId": 7,
        "version": version,
        "fieldValues": [],
        "createdAt": CREATED_AT,
        "createdBy": CREATED_BY,
    }


def changemaker_field_value_batch_payload(
    *, id: int = 1, source_id: int = 1, notes: str | None = "Routine annual import"
) -> dict[str, Any]:
    return {
        "id": id,
        "sourceId": source_id,
        "source": source_payload(id=source_id),
        "notes": notes,
        "createdBy": CREATED_BY,
        "createdAt": CREATED_AT,
    }


def changemaker_field_value_payload(
    *,
    id: int = 1,
    changemaker_id: int = 10,
    batch_id: int = 1,
    short_code: str = "organization_name",
    value: str = "Acme",
    is_valid: bool | None = True,
    batch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": id,
        "changemakerId": changemaker_id,
        "batchId": batch_id,
        "batch": batch if batch is not None else changemaker_field_value_batch_payload(id=batch_id),
        "baseFieldShortCode": short_code,
        "baseField": base_field_payload(short_code),
        "value": value,
        "goodAsOf": CREATED_AT,
        "isValid": is_valid,
        "file": None,
        "createdAt": CREATED_AT,
    }


def bundle(entries: list[dict[str, Any]], *, total: int | None = None) -> dict[str, Any]:
    return {"entries": entries, "total": total if total is not None else len(entries)}


def add_json_response(
    *,
    base_url: str,
    path: str,
    payload: dict[str, Any] | list[Any],
    status: int = 200,
    query_params: dict[str, Any] | None = None,
) -> None:
    add_kwargs: dict[str, Any] = {
        "method": responses.GET,
        "url": f"{base_url.rstrip('/')}/{path.lstrip('/')}",
        "json": payload,
        "status": status,
    }
    if query_params is not None:
        add_kwargs["match"] = [responses.matchers.query_param_matcher({k: str(v) for k, v in query_params.items()})]
    responses.add(**add_kwargs)


def add_changemaker_response(
    *, base_url: str, id: int = 1, status: int = 200, payload: dict[str, Any] | None = None, **payload_kwargs: Any
) -> None:
    add_json_response(
        base_url=base_url,
        path=f"changemakers/{id}",
        payload=payload if payload is not None else changemaker_payload(id=id, **payload_kwargs),
        status=status,
    )


def add_funder_response(
    *,
    base_url: str,
    short_code: str = "acme",
    status: int = 200,
    payload: dict[str, Any] | None = None,
    **payload_kwargs: Any,
) -> None:
    add_json_response(
        base_url=base_url,
        path=f"funders/{short_code}",
        payload=payload if payload is not None else funder_payload(short_code=short_code, **payload_kwargs),
        status=status,
    )


def add_proposal_response(
    *, base_url: str, id: int = 100, status: int = 200, payload: dict[str, Any] | None = None, **payload_kwargs: Any
) -> None:
    add_json_response(
        base_url=base_url,
        path=f"proposals/{id}",
        payload=payload if payload is not None else proposal_payload(id=id, **payload_kwargs),
        status=status,
    )


def add_application_form_response(
    *, base_url: str, id: int = 7, status: int = 200, payload: dict[str, Any] | None = None, **payload_kwargs: Any
) -> None:
    add_json_response(
        base_url=base_url,
        path=f"applicationForms/{id}",
        payload=payload if payload is not None else application_form_payload(id=id, **payload_kwargs),
        status=status,
    )


def add_organization_response(
    *, base_url: str, keycloak_id: str, status: int = 200, payload: dict[str, Any] | None = None, **payload_kwargs: Any
) -> None:
    add_json_response(
        base_url=base_url,
        path=f"organizations/{keycloak_id}",
        payload=payload
        if payload is not None
        else organization_payload(keycloak_organization_id=keycloak_id, **payload_kwargs),
        status=status,
    )


def add_page_response(
    bundle_type: type[PageableBundle],
    *,
    base_url: str,
    payload: dict[str, Any],
    page: int = 1,
    count_per_page: int | None = None,
    content: str | None = None,
    status: int = 200,
    extra_params: dict[str, Any] | None = None,
    path_params: dict[str, Any] | None = None,
) -> None:
    query_params: dict[str, Any] = {"_page": page, "_count": count_per_page or bundle_type.default_page_size}
    if content:
        query_params["_content"] = content
    if extra_params:
        query_params.update(extra_params)
    add_json_response(
        base_url=base_url,
        path=bundle_type.pdc_endpoint.format(**(path_params or {})),
        payload=payload,
        status=status,
        query_params=query_params,
    )
