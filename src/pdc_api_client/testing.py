import responses

CREATED_AT = "2026-01-01T00:00:00Z"
CREATED_BY = "00000000-0000-0000-0000-000000000009"


def changemaker_payload(*, id=1, name="Acme", keycloak_org_id=None, tax_id="12-3456789"):
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


def funder_payload(*, short_code="acme", name="Acme Foundation", keycloak_org_id=None, is_collaborative=False):
    return {
        "shortCode": short_code,
        "name": name,
        "keycloakOrganizationId": keycloak_org_id,
        "isCollaborative": is_collaborative,
        "createdAt": CREATED_AT,
        "createdBy": CREATED_BY,
        "permissions": {},
    }


def data_provider_payload(*, short_code="pdw", name="Philanthropy Data Warehouse", keycloak_org_id=None):
    return {
        "shortCode": short_code,
        "name": name,
        "keycloakOrganizationId": keycloak_org_id,
        "createdAt": CREATED_AT,
        "createdBy": CREATED_BY,
    }


def base_field_payload(short_code="field", *, data_type="string", category="uncategorized"):
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


def proposal_payload(*, id=100, opportunity_id=5, external_id="ext-1"):
    return {
        "id": id,
        "opportunityId": opportunity_id,
        "externalId": external_id,
        "versions": [],
        "changemakers": [],
        "createdAt": CREATED_AT,
        "createdBy": CREATED_BY,
    }


def initiative_payload(*, id=1, changemaker_id=10, title="Summer meals"):
    return {
        "id": id,
        "changemakerId": changemaker_id,
        "title": title,
        "createdAt": CREATED_AT,
        "createdBy": CREATED_BY,
    }


def initiative_field_value_payload(
    *, id=1, initiative_id=1, short_code="field", value="", created_at=CREATED_AT, data_type="string"
):
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


def changemaker_proposal_payload(*, id=1, changemaker_id=10, proposal_id=100):
    return {
        "id": id,
        "changemakerId": changemaker_id,
        "changemaker": changemaker_payload(id=changemaker_id),
        "proposalId": proposal_id,
        "proposal": proposal_payload(id=proposal_id),
        "createdAt": CREATED_AT,
    }


def organization_payload(*, changemaker=None, funder=None, data_provider=None):
    return {"changemaker": changemaker, "funder": funder, "dataProvider": data_provider}


def application_form_payload(*, id=7, version=1, opportunity_id=5):
    return {
        "id": id,
        "version": version,
        "opportunityId": opportunity_id,
        "name": f"Application form {id}",
        "fields": [],
        "createdAt": CREATED_AT,
    }


def source_payload(*, id=1, label="src"):
    return {"id": id, "label": label, "createdAt": CREATED_AT}


def proposal_version_payload(*, id=1, proposal_id=100, version=1):
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


def changemaker_field_value_batch_payload(*, id=1, source_id=1, notes="Routine annual import"):
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
    id=1,
    changemaker_id=10,
    batch_id=1,
    short_code="organization_name",
    value="Acme",
    is_valid=True,
    batch=None,
):
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


def bundle(entries, *, total=None):
    return {"entries": entries, "total": total if total is not None else len(entries)}


def add_json_response(*, base_url, path, payload, status=200, query_params=None):
    add_kwargs = {
        "method": responses.GET,
        "url": f"{base_url.rstrip('/')}/{path.lstrip('/')}",
        "json": payload,
        "status": status,
    }
    if query_params is not None:
        add_kwargs["match"] = [responses.matchers.query_param_matcher({k: str(v) for k, v in query_params.items()})]
    responses.add(**add_kwargs)


def add_changemaker_response(*, base_url, id=1, status=200, payload=None, **payload_kwargs):
    add_json_response(
        base_url=base_url,
        path=f"changemakers/{id}",
        payload=payload if payload is not None else changemaker_payload(id=id, **payload_kwargs),
        status=status,
    )


def add_funder_response(*, base_url, short_code="acme", status=200, payload=None, **payload_kwargs):
    add_json_response(
        base_url=base_url,
        path=f"funders/{short_code}",
        payload=payload if payload is not None else funder_payload(short_code=short_code, **payload_kwargs),
        status=status,
    )


def add_proposal_response(*, base_url, id=100, status=200, payload=None, **payload_kwargs):
    add_json_response(
        base_url=base_url,
        path=f"proposals/{id}",
        payload=payload if payload is not None else proposal_payload(id=id, **payload_kwargs),
        status=status,
    )


def add_application_form_response(*, base_url, id=7, status=200, payload=None, **payload_kwargs):
    add_json_response(
        base_url=base_url,
        path=f"applicationForms/{id}",
        payload=payload if payload is not None else application_form_payload(id=id, **payload_kwargs),
        status=status,
    )


def add_organization_response(*, base_url, keycloak_id, status=200, payload=None, **payload_kwargs):
    add_json_response(
        base_url=base_url,
        path=f"organizations/{keycloak_id}",
        payload=payload if payload is not None else organization_payload(**payload_kwargs),
        status=status,
    )


def add_page_response(
    bundle_type,
    *,
    base_url,
    payload,
    page=1,
    count_per_page=None,
    content=None,
    status=200,
    extra_params=None,
    path_params=None,
):
    query_params = {"_page": page, "_count": count_per_page or bundle_type.default_page_size}
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
