import uuid
from dataclasses import dataclass, field
from typing import Any

from faker import Faker

from pdc_api_client.client import (
    create_changemaker_field_value,
    create_changemaker_field_value_batch,
    create_changemaker_source,
    create_initiative,
    create_initiative_field_value,
    get_bundle_page,
    get_changemaker_field_values,
    get_organization_by_keycloak_id,
)
from pdc_api_client.errors import PDCNotFoundError
from pdc_api_client.models import (
    BaseField,
    ChangemakerBundle,
    ChangemakerFieldValue,
    ChangemakerFieldValueBatch,
    DataProvider,
    Funder,
    Initiative,
    InitiativeFieldValue,
    Opportunity,
    Proposal,
    ProposalVersion,
    ShallowChangemaker,
    Source,
)
from pdc_api_client.seeding.keycloak_admin import KeycloakOrganization
from pdc_api_client.transport import APISession

fake = Faker()


@dataclass
class SeededApplicationForm:
    id: int
    opportunity_id: int
    fields: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SeededProposalBundle:
    changemaker: ShallowChangemaker | None
    funder: Funder
    opportunity: Opportunity
    source: Source
    application_form: SeededApplicationForm
    proposal: Proposal
    proposal_version: ProposalVersion


@dataclass
class SeededChangemakerWithProposals:
    changemaker: ShallowChangemaker
    bundles: list[SeededProposalBundle]


_PREFIX = "seed"

_PROPOSAL_FIELD_LABELS: tuple[tuple[str, str], ...] = (
    ("proposal_name", "Proposal Name"),
    ("proposal_summary", "Proposal Summary"),
    ("proposal_focus", "Proposal Focus"),
    ("proposal_date", "Proposal Date"),
)


def make_proposal_field_seeds(*, include_numbers: bool = False) -> list[tuple[str, str, str]]:
    if include_numbers:
        # Numbers lead the text so they are the first digits a search sees; no thousands separators.
        name = f"#{fake.random_int(min=100, max=9999)} {fake.catch_phrase()}"
        summary = (
            f"Requests ${fake.random_int(min=5_000, max=500_000)} "
            f"over {fake.random_int(min=1, max=5)} years to serve "
            f"{fake.random_int(min=50, max=5_000)} participants. "
            f"{fake.sentence(nb_words=10)}"
        )
    else:
        name = fake.catch_phrase()
        summary = fake.paragraph(nb_sentences=2)
    values_by_short_code = {
        "proposal_name": name,
        "proposal_summary": summary,
        "proposal_focus": fake.bs().title(),
        "proposal_date": fake.date_between(start_date="-3y", end_date="today").isoformat(),
    }
    return [(short_code, label, values_by_short_code[short_code]) for short_code, label in _PROPOSAL_FIELD_LABELS]


def make_changemaker_name(*, include_numbers: bool = False) -> str:
    if include_numbers:
        suffix = fake.random_element(("Foundation", "Initiative", "Collective", "Project", "Alliance"))
        return f"{fake.last_name()} {fake.random_int(min=100, max=9999)} {suffix}"
    return fake.company()


def _token(label: str) -> str:
    return f"{_PREFIX}_{label}_{uuid.uuid4().hex[:8]}"


def seed_base_field(
    session: APISession,
    *,
    short_code: str | None = None,
    label: str | None = None,
    data_type: str = "string",
    category: str = "project",
    sensitivity_classification: str = "public",
) -> BaseField:
    short_code = short_code or _token("field")
    label = label or f"Test Field {short_code}"
    response = session.put(
        f"/baseFields/{short_code}",
        json={
            "label": label,
            "description": f"Integration test base field: {short_code}",
            "dataType": data_type,
            "category": category,
            "sensitivityClassification": sensitivity_classification,
            "valueRelevanceHours": None,
        },
    )
    return BaseField.model_validate(response.json())


_FUNDER_NAME_SUFFIXES: tuple[str, ...] = (
    "Foundation",
    "Fund",
    "Trust",
    "Endowment",
    "Philanthropies",
)
_COLLABORATIVE_NAME_SUFFIXES: tuple[str, ...] = (
    "Collaborative",
    "Funders Collaborative",
    "Pooled Fund",
    "Funder Alliance",
    "Giving Circle",
)


def make_funder_name(*, is_collaborative: bool = False) -> str:
    suffixes = _COLLABORATIVE_NAME_SUFFIXES if is_collaborative else _FUNDER_NAME_SUFFIXES
    return f"{fake.last_name()} {fake.random_element(suffixes)}"


def seed_funder(
    session: APISession,
    *,
    short_code: str | None = None,
    name: str | None = None,
    is_collaborative: bool = False,
    keycloak_organization_id: str | None = None,
) -> Funder:
    short_code = short_code or _token("funder")
    name = name or make_funder_name(is_collaborative=is_collaborative)
    body: dict[str, Any] = {"name": name, "isCollaborative": is_collaborative}
    if keycloak_organization_id is not None:
        body["keycloakOrganizationId"] = keycloak_organization_id
    response = session.put(f"/funders/{short_code}", json=body)
    return Funder.model_validate(response.json())


def seed_funder_collaborative_member(
    session: APISession,
    *,
    collaborative: Funder,
    member: Funder,
) -> dict[str, Any]:
    response = session.post(
        f"/funders/{collaborative.short_code}/members/{member.short_code}",
    )
    payload: dict[str, Any] = response.json()
    return payload


@dataclass
class SeededFunderCollaborative:
    collaborative: Funder
    members: list[Funder]


def seed_funder_collaborative_with_members(
    session: APISession,
    *,
    member_count: int,
    name: str | None = None,
) -> SeededFunderCollaborative:
    collaborative = seed_funder(session, name=name, is_collaborative=True)
    members = [seed_funder(session, is_collaborative=False) for _ in range(member_count)]
    for member in members:
        seed_funder_collaborative_member(session, collaborative=collaborative, member=member)
    return SeededFunderCollaborative(collaborative=collaborative, members=members)


@dataclass
class SeededFunderVariety:
    standalones: list[Funder]
    collaborative: SeededFunderCollaborative


def seed_funder_variety(
    session: APISession,
    *,
    standalone_count: int = 6,
    collaborative_member_count: int = 3,
) -> SeededFunderVariety:
    standalones = [seed_funder(session, is_collaborative=False) for _ in range(standalone_count)]
    collaborative = seed_funder_collaborative_with_members(session, member_count=collaborative_member_count)
    return SeededFunderVariety(standalones=standalones, collaborative=collaborative)


def seed_changemaker(
    session: APISession,
    *,
    name: str | None = None,
    tax_id: str | None = None,
    keycloak_organization_id: str | None = None,
) -> ShallowChangemaker:
    name = name or make_changemaker_name()
    # PDC has no changemaker upsert, so a caller-supplied tax_id is looked up first to stay idempotent.
    if tax_id is not None:
        existing = _find_changemaker_by_tax_id(session, tax_id)
        if existing is not None:
            return existing
    else:
        tax_id = f"XX-{uuid.uuid4().hex[:7]}"
    body: dict[str, Any] = {"name": name, "taxId": tax_id}
    if keycloak_organization_id is not None:
        body["keycloakOrganizationId"] = keycloak_organization_id
    response = session.post("/changemakers", json=body)
    return ShallowChangemaker.model_validate(response.json())


def _find_changemaker_by_tax_id(session: APISession, tax_id: str) -> ShallowChangemaker | None:
    # PDC's _content search matches names only, so page through every changemaker.
    page = 1
    page_size = 100
    while True:
        bundle = get_bundle_page(session, ChangemakerBundle, page=page, count_per_page=page_size)
        for entry in bundle.entries:
            if entry.tax_id == tax_id:
                return entry
        if not bundle.entries or page * page_size >= bundle.total:
            return None
        page += 1


def seed_opportunity(
    session: APISession,
    *,
    funder: Funder | None = None,
    title: str | None = None,
) -> Opportunity:
    if funder is None:
        funder = seed_funder(session)
    title = title or f"{fake.catch_phrase()} Grant"
    response = session.post(
        "/opportunities",
        json={"title": title, "funderShortCode": funder.short_code},
    )
    return Opportunity.model_validate(response.json())


def seed_data_provider(
    session: APISession,
    *,
    short_code: str | None = None,
    name: str | None = None,
    keycloak_organization_id: str | None = None,
) -> DataProvider:
    short_code = short_code or _token("dp")
    name = name or f"{fake.company()} Data"
    body: dict[str, Any] = {"name": name}
    if keycloak_organization_id is not None:
        body["keycloakOrganizationId"] = keycloak_organization_id
    response = session.put(f"/dataProviders/{short_code}", json=body)
    return DataProvider.model_validate(response.json())


def _kc_alias_slug(kc_org: KeycloakOrganization) -> str:
    # Keycloak aliases are kebab-case; PDC short codes are snake_case.
    return kc_org.alias.replace("-", "_")


def ensure_funder_for_kc_org(
    session: APISession,
    *,
    kc_org: KeycloakOrganization,
    name: str,
    is_collaborative: bool = False,
) -> Funder:
    try:
        org = get_organization_by_keycloak_id(session, keycloak_id=kc_org.id)
        if org.funder is not None:
            return org.funder
    except PDCNotFoundError:
        pass
    return seed_funder(
        session,
        short_code=f"{_kc_alias_slug(kc_org)}_funder",
        name=name,
        is_collaborative=is_collaborative,
        keycloak_organization_id=kc_org.id,
    )


def ensure_changemaker_for_kc_org(
    session: APISession,
    *,
    kc_org: KeycloakOrganization,
    name: str,
) -> ShallowChangemaker:
    try:
        org = get_organization_by_keycloak_id(session, keycloak_id=kc_org.id)
        if org.changemaker is not None:
            return org.changemaker
    except PDCNotFoundError:
        pass
    return seed_changemaker(session, name=name, keycloak_organization_id=kc_org.id)


def ensure_data_provider_for_kc_org(
    session: APISession,
    *,
    kc_org: KeycloakOrganization,
    name: str,
) -> DataProvider:
    try:
        org = get_organization_by_keycloak_id(session, keycloak_id=kc_org.id)
        if org.data_provider is not None:
            return org.data_provider
    except PDCNotFoundError:
        pass
    return seed_data_provider(
        session,
        short_code=f"{_kc_alias_slug(kc_org)}_data_provider",
        name=name,
        keycloak_organization_id=kc_org.id,
    )


def seed_fiscal_sponsorship(
    session: APISession,
    *,
    sponsee: ShallowChangemaker,
    sponsor: ShallowChangemaker,
    not_after: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if not_after is not None:
        body["notAfter"] = not_after
    response = session.put(
        f"/changemakers/{sponsee.id}/fiscalSponsors/{sponsor.id}",
        json=body,
    )
    payload: dict[str, Any] = response.json()
    return payload


def seed_funder_collaborative_invitation(
    session: APISession,
    *,
    collaborative: Funder,
    invited: Funder,
) -> dict[str, Any]:
    response = session.post(
        f"/funders/{collaborative.short_code}/invitations/sent/{invited.short_code}",
        # PDC rejects a missing body even though no fields are required.
        json={},
    )
    payload: dict[str, Any] = response.json()
    return payload


def respond_to_funder_collaborative_invitation(
    session: APISession,
    *,
    collaborative: Funder,
    invited: Funder,
    status: str,
) -> dict[str, Any]:
    response = session.patch(
        f"/funders/{invited.short_code}/invitations/received/{collaborative.short_code}",
        json={"invitationStatus": status},
    )
    payload: dict[str, Any] = response.json()
    return payload


def seed_source(
    session: APISession,
    *,
    label: str | None = None,
    data_provider_short_code: str | None = None,
    funder_short_code: str | None = None,
    changemaker_id: int | None = None,
) -> Source:
    label = label or f"{fake.catch_phrase()} Source"
    if changemaker_id is not None:
        return create_changemaker_source(session, changemaker_id=changemaker_id, label=label)
    payload: dict[str, Any] = {"label": label}
    if data_provider_short_code:
        payload["dataProviderShortCode"] = data_provider_short_code
    elif funder_short_code:
        payload["funderShortCode"] = funder_short_code
    else:
        funder = seed_funder(session)
        payload["funderShortCode"] = funder.short_code
    response = session.post("/sources", json=payload)
    return Source.model_validate(response.json())


def seed_initiative(session: APISession, *, changemaker_id: int, title: str | None = None) -> Initiative:
    return create_initiative(session, changemaker_id=changemaker_id, title=title or fake.catch_phrase())


def seed_initiative_field_value(
    session: APISession,
    *,
    initiative_id: int,
    base_field_short_code: str,
    source: Source,
    value: str,
) -> InitiativeFieldValue:
    return create_initiative_field_value(
        session,
        initiative_id=initiative_id,
        base_field_short_code=base_field_short_code,
        value=value,
        source_id=source.id,
    )


def seed_application_form(
    session: APISession,
    *,
    opportunity: Opportunity | None = None,
    base_field_short_codes: list[str] | None = None,
    name: str | None = None,
) -> SeededApplicationForm:
    if opportunity is None:
        opportunity = seed_opportunity(session)
    fields = []
    if base_field_short_codes:
        fields = [
            {
                "baseFieldShortCode": sc,
                "position": i + 1,
                "label": f"Field {sc}",
                "instructions": None,
                "inputType": None,
            }
            for i, sc in enumerate(base_field_short_codes)
        ]
    response = session.post(
        "/applicationForms",
        json={
            "opportunityId": opportunity.id,
            "name": name or f"Test Application Form {uuid.uuid4().hex[:8]}",
            "fields": fields,
        },
    )
    data = response.json()
    return SeededApplicationForm(
        id=data["id"],
        opportunity_id=opportunity.id,
        fields=data.get("fields", []),
    )


def seed_proposal(
    session: APISession,
    *,
    opportunity: Opportunity | None = None,
    external_id: str | None = None,
) -> Proposal:
    if opportunity is None:
        opportunity = seed_opportunity(session)
    external_id = external_id or _token("proposal")
    response = session.post(
        "/proposals",
        json={
            "opportunityId": opportunity.id,
            "externalId": external_id,
        },
    )
    return Proposal.model_validate(response.json())


def seed_proposal_version(
    session: APISession,
    *,
    proposal: Proposal,
    source: Source,
    application_form: SeededApplicationForm,
    field_values: list[dict[str, Any]] | None = None,
) -> ProposalVersion:
    response = session.post(
        "/proposalVersions",
        json={
            "proposalId": proposal.id,
            "sourceId": source.id,
            "applicationFormId": application_form.id,
            "fieldValues": field_values or [],
        },
    )
    return ProposalVersion.model_validate(response.json())


def link_changemaker_to_proposal(
    session: APISession,
    *,
    changemaker: ShallowChangemaker,
    proposal: Proposal,
) -> dict[str, Any]:
    response = session.post(
        "/changemakerProposals",
        json={
            "changemakerId": changemaker.id,
            "proposalId": proposal.id,
        },
    )
    payload: dict[str, Any] = response.json()
    return payload


_CHANGEMAKER_PROFILE_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("organization_legal_name", "Legal name", "string"),
    ("organization_website", "Website", "url"),
    ("organization_mission_statement", "Mission statement", "string"),
    ("organization_street_address_1", "Street address", "string"),
    ("organization_city", "City", "string"),
    ("organization_state_province", "State / province", "string"),
    ("organization_postal_code", "Postal code", "string"),
    ("organization_country", "Country", "string"),
)


def make_changemaker_profile_field_seeds(*, name: str) -> list[tuple[str, str, str, str]]:
    values_by_short_code = {
        "organization_legal_name": f"{name} Inc.",
        "organization_website": f"https://www.{fake.domain_name()}",
        "organization_mission_statement": fake.paragraph(nb_sentences=2),
        "organization_street_address_1": fake.street_address(),
        "organization_city": fake.city(),
        "organization_state_province": fake.state(),
        "organization_postal_code": fake.postcode(),
        "organization_country": "United States",
    }
    return [
        (short_code, label, data_type, values_by_short_code[short_code])
        for short_code, label, data_type in _CHANGEMAKER_PROFILE_FIELDS
    ]


@dataclass
class SeededChangemakerProfile:
    changemaker: ShallowChangemaker
    source: Source
    batch: ChangemakerFieldValueBatch
    field_values: list[ChangemakerFieldValue]


def seed_changemaker_profile_fields(
    session: APISession,
    *,
    changemaker: ShallowChangemaker,
    data_provider: DataProvider,
    source_label: str | None = None,
    notes: str | None = "Seeded organization profile import",
) -> SeededChangemakerProfile | None:
    existing = get_changemaker_field_values(session, changemaker_id=changemaker.id)
    if any(field_value.batch is not None for field_value in existing):
        return None
    field_seeds = make_changemaker_profile_field_seeds(name=changemaker.name)
    for short_code, label, data_type, _ in field_seeds:
        seed_base_field(session, short_code=short_code, label=label, data_type=data_type, category="organization")
    source = seed_source(
        session,
        label=source_label or f"{data_provider.name} nonprofit profiles",
        data_provider_short_code=data_provider.short_code,
    )
    batch = create_changemaker_field_value_batch(session, source_id=source.id, notes=notes)
    field_values = [
        create_changemaker_field_value(
            session,
            changemaker_id=changemaker.id,
            base_field_short_code=short_code,
            batch_id=batch.id,
            value=value,
        )
        for short_code, _, _, value in field_seeds
    ]
    return SeededChangemakerProfile(changemaker=changemaker, source=source, batch=batch, field_values=field_values)


def seed_proposal_bundle(
    session: APISession,
    *,
    field_seeds: list[tuple[str, str, str]] | None = None,
    changemaker_name: str | None = None,
    field_sensitivity_classification: str = "public",
) -> SeededProposalBundle:
    # Base fields upsert by short_code across the whole stack, so a non-public sensitivity needs unique short codes.
    if field_seeds is None:
        field_seeds = make_proposal_field_seeds()
    seeded_fields = [
        seed_base_field(
            session, short_code=short_code, label=label, sensitivity_classification=field_sensitivity_classification
        )
        for short_code, label, _ in field_seeds
    ]
    funder = seed_funder(session)
    changemaker = seed_changemaker(session, name=changemaker_name)
    opportunity = seed_opportunity(session, funder=funder)

    source = seed_source(
        session,
        funder_short_code=funder.short_code,
    )
    application_form = seed_application_form(
        session,
        opportunity=opportunity,
        base_field_short_codes=[bf.short_code for bf in seeded_fields],
    )
    form_field_id_by_short_code = {
        form_field["baseFieldShortCode"]: form_field["id"] for form_field in application_form.fields
    }

    proposal = seed_proposal(session, opportunity=opportunity)
    proposal_version = seed_proposal_version(
        session,
        proposal=proposal,
        source=source,
        application_form=application_form,
        field_values=[
            {
                "applicationFormFieldId": form_field_id_by_short_code[short_code],
                "position": position,
                "value": value,
                "goodAsOf": None,
            }
            for position, (short_code, _, value) in enumerate(field_seeds, start=1)
        ],
    )

    link_changemaker_to_proposal(
        session,
        changemaker=changemaker,
        proposal=proposal,
    )

    return SeededProposalBundle(
        changemaker=changemaker,
        funder=funder,
        opportunity=opportunity,
        source=source,
        application_form=application_form,
        proposal=proposal,
        proposal_version=proposal_version,
    )


def seed_changemaker_with_proposals(
    session: APISession,
    *,
    proposal_count: int,
    changemaker_name: str | None = None,
    changemaker: ShallowChangemaker | None = None,
    funder: Funder | None = None,
) -> SeededChangemakerWithProposals:
    if changemaker is None:
        changemaker = seed_changemaker(session, name=changemaker_name)
    field_labels = make_proposal_field_seeds()
    seeded_fields = [
        seed_base_field(session, short_code=short_code, label=label) for short_code, label, _ in field_labels
    ]
    if funder is None:
        funder = seed_funder(session)
    opportunity = seed_opportunity(session, funder=funder)
    source = seed_source(session, funder_short_code=funder.short_code)
    application_form = seed_application_form(
        session,
        opportunity=opportunity,
        base_field_short_codes=[bf.short_code for bf in seeded_fields],
    )
    form_field_id_by_short_code = {
        form_field["baseFieldShortCode"]: form_field["id"] for form_field in application_form.fields
    }

    bundles: list[SeededProposalBundle] = []
    for i in range(proposal_count):
        field_seeds = make_proposal_field_seeds(include_numbers=i % 2 == 0)
        proposal = seed_proposal(session, opportunity=opportunity)
        proposal_version = seed_proposal_version(
            session,
            proposal=proposal,
            source=source,
            application_form=application_form,
            field_values=[
                {
                    "applicationFormFieldId": form_field_id_by_short_code[short_code],
                    "position": position,
                    "value": value,
                    "goodAsOf": None,
                }
                for position, (short_code, _, value) in enumerate(field_seeds, start=1)
            ],
        )
        link_changemaker_to_proposal(session, changemaker=changemaker, proposal=proposal)
        bundles.append(
            SeededProposalBundle(
                changemaker=changemaker,
                funder=funder,
                opportunity=opportunity,
                source=source,
                application_form=application_form,
                proposal=proposal,
                proposal_version=proposal_version,
            )
        )

    return SeededChangemakerWithProposals(changemaker=changemaker, bundles=bundles)


def seed_proposal_corpus(
    session: APISession,
    *,
    size: int = 4,
) -> list[SeededProposalBundle]:
    bundles: list[SeededProposalBundle] = []
    for i in range(size):
        include_numbers = i % 2 == 0
        bundles.append(
            seed_proposal_bundle(
                session,
                field_seeds=make_proposal_field_seeds(include_numbers=include_numbers),
                changemaker_name=make_changemaker_name(include_numbers=include_numbers),
            )
        )
    return bundles
