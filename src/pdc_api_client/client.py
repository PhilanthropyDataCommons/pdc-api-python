import json
from collections.abc import Generator
from datetime import datetime
from typing import Any, ClassVar, Protocol, Self

import requests

from pdc_api_client import errors
from pdc_api_client.models import (
    BaseField,
    Changemaker,
    ChangemakerApplicationForm,
    ChangemakerFieldValue,
    ChangemakerFieldValueBatch,
    ChangemakerProposal,
    DataProvider,
    File,
    Funder,
    Initiative,
    InitiativeFieldValue,
    NewProposalVersion,
    Organization,
    PresignedPost,
    Proposal,
    ProposalVersion,
    Source,
)
from pdc_api_client.transport import APISession


def _iterate_pages(
    session: APISession,
    *,
    endpoint: str,
    params: dict[str, Any] | None = None,
    count_per_page: int = 50,
    max_requests: int | None = None,
    **kwargs: Any,
) -> Generator[dict[str, Any], None, None]:
    params = params or {}
    page = 1
    n_pages = None
    while n_pages is None or page <= n_pages:
        params.update({"_page": page, "_count": count_per_page})
        response = session.get(endpoint, params=params, **kwargs)
        payload = response.json()
        if n_pages is None:
            total = payload["total"]
            n_pages = (total + count_per_page - 1) // count_per_page
        yield payload
        page += 1
        if max_requests is not None and page > max_requests:
            break
        if "entries" in payload and len(payload["entries"]) < count_per_page:
            # A short page is the last one, even if "total" disagrees.
            break


def get_basefields(session: APISession) -> list[BaseField]:
    return [
        BaseField.model_validate(entry)
        for payload in _iterate_pages(session, endpoint="/baseFields", count_per_page=10_000)
        for entry in payload["entries"]
    ]


def get_changemakers(session: APISession) -> Generator[Changemaker, None, None]:
    for payload in _iterate_pages(session, endpoint="/changemakers"):
        for entry in payload["entries"]:
            yield Changemaker.model_validate(entry)


def get_funders(session: APISession) -> Generator[Funder, None, None]:
    for payload in _iterate_pages(session, endpoint="/funders"):
        for entry in payload["entries"]:
            yield Funder.model_validate(entry)


def get_data_providers(session: APISession) -> Generator[DataProvider, None, None]:
    for payload in _iterate_pages(session, endpoint="/dataProviders"):
        for entry in payload["entries"]:
            yield DataProvider.model_validate(entry)


def get_changemaker_proposals(
    session: APISession,
    *,
    changemaker_id: int | None = None,
    proposal_id: int | None = None,
    count_per_page: int | None = None,
) -> Generator[ChangemakerProposal, None, None]:
    endpoint = "/changemakerProposals"
    query_params = {}
    if changemaker_id is not None:
        query_params["changemaker"] = changemaker_id
    if proposal_id is not None:
        query_params["proposal"] = proposal_id

    page_kwargs = {} if count_per_page is None else {"count_per_page": count_per_page}
    for payload in _iterate_pages(session, endpoint=endpoint, params=query_params, **page_kwargs):
        for entry in payload["entries"]:
            yield ChangemakerProposal.model_validate(entry)


def get_proposals(session: APISession, *, count_per_page: int = 50) -> Generator[Proposal, None, None]:
    for payload in _iterate_pages(session, endpoint="/proposals", count_per_page=count_per_page):
        for entry in payload["entries"]:
            yield Proposal.model_validate(entry)


def get_initiatives(session: APISession, *, changemaker_id: int | None = None) -> Generator[Initiative, None, None]:
    params = {} if changemaker_id is None else {"changemaker": changemaker_id}
    for payload in _iterate_pages(session, endpoint="/initiatives", params=params):
        for entry in payload["entries"]:
            yield Initiative.model_validate(entry)


def get_initiative(session: APISession, *, initiative_id: int) -> Initiative:
    response = session.get(f"initiatives/{initiative_id}")
    return Initiative.model_validate(response.json())


def get_initiative_field_values(
    session: APISession, *, initiative_id: int
) -> Generator[InitiativeFieldValue, None, None]:
    for payload in _iterate_pages(session, endpoint=f"/initiatives/{initiative_id}/fieldValues"):
        for entry in payload["entries"]:
            yield InitiativeFieldValue.model_validate(entry)


def _good_as_of_json(good_as_of: datetime | None) -> str | None:
    if good_as_of is None:
        return None
    if good_as_of.tzinfo is None:
        raise ValueError("good_as_of must include a timezone")
    return good_as_of.isoformat()


def create_initiative(session: APISession, *, changemaker_id: int, title: str) -> Initiative:
    response = session.post("initiatives", json={"changemakerId": changemaker_id, "title": title})
    return Initiative.model_validate(response.json())


def create_initiative_field_value(
    session: APISession,
    *,
    initiative_id: int,
    base_field_short_code: str,
    value: str,
    source_id: int,
    good_as_of: datetime | None = None,
) -> InitiativeFieldValue:
    response = session.post(
        f"initiatives/{initiative_id}/fieldValues",
        json={
            "baseFieldShortCode": base_field_short_code,
            "value": value,
            "sourceId": source_id,
            "goodAsOf": _good_as_of_json(good_as_of),
        },
    )
    return InitiativeFieldValue.model_validate(response.json())


def get_organization_by_keycloak_id(session: APISession, *, keycloak_id: str) -> Organization:
    response = session.get(f"organizations/{keycloak_id}")
    return Organization.model_validate(response.json())


def get_application_form(session: APISession, *, form_id: int) -> ChangemakerApplicationForm:
    response = session.get(f"applicationForms/{form_id}")
    return ChangemakerApplicationForm.model_validate(response.json())


def get_application_form_by_name(session: APISession, *, name: str) -> ChangemakerApplicationForm:
    for payload in _iterate_pages(session, endpoint="/applicationForms"):
        for entry in payload["entries"]:
            if entry["name"] == name:
                return ChangemakerApplicationForm.model_validate(entry)
    raise errors.ApplicationFormNotFoundError(detail=f"No application form named {name!r}")


def create_changemaker_proposal(session: APISession, *, data: dict[str, Any]) -> Proposal:
    response = session.post("proposals", json=data)
    return Proposal.model_validate(response.json())


def create_changemaker_proposal_version(
    session: APISession, *, proposal_version: NewProposalVersion
) -> ProposalVersion:
    response = session.post("proposalVersions", json=json.loads(proposal_version.model_dump_json(by_alias=True)))
    return ProposalVersion.model_validate(response.json())


def link_changemaker_to_proposal(session: APISession, *, changemaker_id: int, proposal_id: int) -> ChangemakerProposal:
    response = session.post("changemakerProposals", json={"changemakerId": changemaker_id, "proposalId": proposal_id})
    return ChangemakerProposal.model_validate(response.json())


def get_changemaker_proposal(session: APISession, *, proposal_id: int) -> ChangemakerProposal:
    response = session.get("changemakerProposals", params={"proposal": proposal_id})
    try:
        return ChangemakerProposal.model_validate(response.json()["entries"][0])
    except (KeyError, IndexError):
        raise errors.ProposalNotFoundError


def get_proposal(session: APISession, *, proposal_id: int) -> Proposal:
    try:
        response = session.get(f"proposals/{proposal_id}")
    except errors.PDCNotFoundError:
        raise errors.ProposalNotFoundError
    return Proposal.model_validate(response.json())


def get_changemaker(session: APISession, *, changemaker_id: int) -> Changemaker:
    try:
        response = session.get(f"changemakers/{changemaker_id}")
        return Changemaker.model_validate(response.json())
    except errors.PDCNotFoundError:
        raise errors.ChangemakerNotFoundError


def get_changemaker_field_values(
    session: APISession,
    *,
    changemaker_id: int | None = None,
    batch_id: int | None = None,
) -> Generator[ChangemakerFieldValue, None, None]:
    params = {}
    if changemaker_id is not None:
        params["changemaker"] = changemaker_id
    if batch_id is not None:
        params["changemakerFieldValueBatch"] = batch_id
    for payload in _iterate_pages(session, endpoint="/changemakerFieldValues", params=params):
        for entry in payload["entries"]:
            yield ChangemakerFieldValue.model_validate(entry)


def get_changemaker_field_value_batch(session: APISession, *, batch_id: int) -> ChangemakerFieldValueBatch:
    try:
        response = session.get(f"changemakerFieldValueBatches/{batch_id}")
    except errors.PDCNotFoundError:
        raise errors.ChangemakerFieldValueBatchNotFoundError
    return ChangemakerFieldValueBatch.model_validate(response.json())


def create_changemaker_source(session: APISession, *, changemaker_id: int, label: str) -> Source:
    response = session.post("sources", json={"changemakerId": changemaker_id, "label": label})
    return Source.model_validate(response.json())


def create_changemaker_field_value_batch(
    session: APISession, *, source_id: int, notes: str | None = None
) -> ChangemakerFieldValueBatch:
    response = session.post("changemakerFieldValueBatches", json={"sourceId": source_id, "notes": notes})
    return ChangemakerFieldValueBatch.model_validate(response.json())


def create_changemaker_field_value(
    session: APISession,
    *,
    changemaker_id: int,
    base_field_short_code: str,
    batch_id: int,
    value: str,
    good_as_of: datetime | None = None,
) -> ChangemakerFieldValue:
    response = session.post(
        "changemakerFieldValues",
        json={
            "changemakerId": changemaker_id,
            "baseFieldShortCode": base_field_short_code,
            "batchId": batch_id,
            "value": value,
            "goodAsOf": _good_as_of_json(good_as_of),
        },
    )
    return ChangemakerFieldValue.model_validate(response.json())


def get_funder(session: APISession, *, short_code: str) -> Funder:
    try:
        response = session.get(f"funders/{short_code}")
    except errors.PDCNotFoundError as exc:
        raise errors.FunderNotFoundError(short_code) from exc
    return Funder.model_validate(response.json())


class PageableBundle(Protocol):
    pdc_endpoint: ClassVar[str]
    default_page_size: ClassVar[int]

    @classmethod
    def model_validate(cls, obj: Any) -> Self: ...


def get_bundle_page[BundleT: PageableBundle](
    session: APISession,
    bundle_type: type[BundleT],
    *,
    page: int = 1,
    count_per_page: int | None = None,
    content: str | None = None,
    extra_params: dict[str, Any] | None = None,
    path_params: dict[str, Any] | None = None,
) -> BundleT:
    params: dict[str, Any] = {"_page": page, "_count": count_per_page or bundle_type.default_page_size}
    if content:
        params["_content"] = content
    if extra_params:
        params.update(extra_params)
    endpoint = bundle_type.pdc_endpoint.format(**(path_params or {}))
    response = session.get(endpoint, params=params)
    return bundle_type.model_validate(response.json())


def register_file_upload(session: APISession, *, name: str, mime_type: str, size: int) -> File:
    response = session.post("files", json={"name": name, "mimeType": mime_type, "size": size})
    return File(**response.json())


def upload_file_to_s3_presigned_url(
    *, presigned_post: PresignedPost, file_data: bytes, file_name: str, content_type: str
) -> None:
    fields = {**presigned_post.fields, "Content-Type": content_type}
    files = {"file": (file_name, file_data, content_type)}
    try:
        response = requests.post(presigned_post.url, data=fields, files=files, timeout=120)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise errors.PDCServiceError(detail=f"Failed to upload file to S3: {exc}") from exc
