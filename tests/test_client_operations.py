import json
from datetime import UTC, datetime

import pytest
import responses

from pdc_api_client.client import (
    create_changemaker_field_value,
    create_changemaker_field_value_batch,
    create_changemaker_proposal,
    create_changemaker_proposal_version,
    create_changemaker_source,
    get_application_form,
    get_application_form_by_name,
    get_bundle_page,
    get_changemaker,
    get_changemaker_proposal,
    get_funder,
    get_organization_by_keycloak_id,
    get_proposal,
    link_changemaker_to_proposal,
    register_file_upload,
)
from pdc_api_client.errors import (
    ApplicationFormNotFoundError,
    ChangemakerNotFoundError,
    FunderNotFoundError,
    ProposalNotFoundError,
)
from pdc_api_client.models import (
    ChangemakerBundle,
    ChangemakerProposal,
    FunderCollaborativeMemberBundle,
    NewProposalFieldValue,
    NewProposalVersion,
    Organization,
)
from pdc_api_client.testing import (
    application_form_payload,
    bundle,
    changemaker_field_value_batch_payload,
    changemaker_field_value_payload,
    changemaker_payload,
    changemaker_proposal_payload,
    funder_payload,
    proposal_payload,
    proposal_version_payload,
    source_payload,
)

BASE_URL = "https://pdc.test"


def _post(path, payload):
    responses.add(responses.POST, f"{BASE_URL}/{path}", json=payload)


def _sent_json():
    return json.loads(responses.calls[-1].request.body)


class TestGetProposal:
    def test_404_translates_to_proposal_not_found(self, session, add_proposal_response):
        add_proposal_response(id=999, status=404, payload={})

        with pytest.raises(ProposalNotFoundError):
            get_proposal(session, proposal_id=999)


class TestGetChangemaker:
    def test_404_translates_to_changemaker_not_found(self, session, add_changemaker_response):
        add_changemaker_response(id=999, status=404, payload={})

        with pytest.raises(ChangemakerNotFoundError):
            get_changemaker(session, changemaker_id=999)


class TestGetFunder:
    def test_404_translates_to_funder_not_found(self, session, add_funder_response):
        add_funder_response(short_code="missing", status=404, payload={})

        with pytest.raises(FunderNotFoundError):
            get_funder(session, short_code="missing")


class TestGetChangemakerProposal:
    def test_returns_first_entry_as_model(self, session, add_json_response):
        add_json_response(
            path="changemakerProposals",
            payload=bundle([changemaker_proposal_payload(id=5)]),
            query_params={"proposal": 100},
        )

        result = get_changemaker_proposal(session, proposal_id=100)

        assert isinstance(result, ChangemakerProposal)
        assert result.id == 5

    def test_empty_bundle_translates_to_proposal_not_found(self, session, add_json_response):
        add_json_response(path="changemakerProposals", payload=bundle([]), query_params={"proposal": 100})

        with pytest.raises(ProposalNotFoundError):
            get_changemaker_proposal(session, proposal_id=100)


class TestGetOrganizationByKeycloakId:
    def test_parses_organization_with_funder_facet(self, session, add_organization_response):
        add_organization_response(keycloak_id="kc-uuid", funder=funder_payload(short_code="acme"))

        result = get_organization_by_keycloak_id(session, keycloak_id="kc-uuid")

        assert isinstance(result, Organization)
        assert result.funder.short_code == "acme"
        assert result.changemaker is None


class TestGetApplicationForm:
    def test_requests_form_by_id(self, session, add_application_form_response):
        add_application_form_response(id=7)

        get_application_form(session, form_id=7)

        assert responses.calls[-1].request.path_url == "/applicationForms/7"


class TestGetApplicationFormByName:
    def _add_forms(self, *names):
        forms = [{**application_form_payload(id=i), "name": name} for i, name in enumerate(names, start=1)]
        responses.add(responses.GET, f"{BASE_URL}/applicationForms", json=bundle(forms))

    def test_returns_form_with_matching_name(self, session):
        self._add_forms("Other", "Wanted")

        assert get_application_form_by_name(session, name="Wanted").id == 2

    def test_raises_not_found_when_no_form_has_the_name(self, session):
        self._add_forms("Other")

        with pytest.raises(ApplicationFormNotFoundError):
            get_application_form_by_name(session, name="Wanted")


class TestCreateChangemakerProposal:
    def test_sends_data_unchanged(self, session):
        _post("proposals", proposal_payload())

        create_changemaker_proposal(session, data={"opportunityId": 5, "externalId": "ext-1"})

        assert _sent_json() == {"opportunityId": 5, "externalId": "ext-1"}


class TestCreateChangemakerProposalVersion:
    def test_sends_camel_case_body(self, session):
        new_version = NewProposalVersion(
            proposal_id=100,
            source_id=1,
            application_form_id=7,
            field_values=[NewProposalFieldValue(application_form_field_id=3, position=1, value="hi")],
        )
        _post("proposalVersions", proposal_version_payload())

        create_changemaker_proposal_version(session, proposal_version=new_version)

        assert _sent_json() == {
            "proposalId": 100,
            "sourceId": 1,
            "applicationFormId": 7,
            "fieldValues": [{"applicationFormFieldId": 3, "position": 1, "value": "hi", "goodAsOf": None}],
        }


class TestLinkChangemakerToProposal:
    def test_sends_changemaker_and_proposal_ids(self, session):
        _post("changemakerProposals", changemaker_proposal_payload())

        link_changemaker_to_proposal(session, changemaker_id=10, proposal_id=100)

        assert _sent_json() == {"changemakerId": 10, "proposalId": 100}


class TestRegisterFileUpload:
    def test_sends_file_metadata(self, session):
        _post("files", {"id": 3, "name": "doc.pdf"})

        register_file_upload(session, name="doc.pdf", mime_type="application/pdf", size=42)

        assert _sent_json() == {"name": "doc.pdf", "mimeType": "application/pdf", "size": 42}


class TestCreateChangemakerSource:
    def test_sends_changemaker_and_label(self, session):
        _post("sources", source_payload())

        create_changemaker_source(session, changemaker_id=10, label="Acme (self-reported)")

        assert _sent_json() == {"changemakerId": 10, "label": "Acme (self-reported)"}


class TestCreateChangemakerFieldValueBatch:
    def test_sends_source_and_notes(self, session):
        _post("changemakerFieldValueBatches", changemaker_field_value_batch_payload())

        create_changemaker_field_value_batch(session, source_id=42, notes="Edited")

        assert _sent_json() == {"sourceId": 42, "notes": "Edited"}


class TestCreateChangemakerFieldValue:
    @pytest.mark.parametrize(
        ("good_as_of", "sent"),
        [(datetime(2026, 1, 31, 9, 0, tzinfo=UTC), "2026-01-31T09:00:00+00:00"), (None, None)],
    )
    def test_sends_good_as_of_as_iso_string(self, session, good_as_of, sent):
        _post("changemakerFieldValues", changemaker_field_value_payload())

        create_changemaker_field_value(
            session,
            changemaker_id=10,
            base_field_short_code="organization_city",
            batch_id=20,
            value="Springfield",
            good_as_of=good_as_of,
        )

        assert _sent_json() == {
            "changemakerId": 10,
            "baseFieldShortCode": "organization_city",
            "batchId": 20,
            "value": "Springfield",
            "goodAsOf": sent,
        }

    def test_rejects_good_as_of_without_timezone(self, session):
        with pytest.raises(ValueError, match="good_as_of must include a timezone"):
            create_changemaker_field_value(
                session,
                changemaker_id=10,
                base_field_short_code="organization_city",
                batch_id=20,
                value="Springfield",
                good_as_of=datetime(2026, 1, 31, 9, 0),
            )

        assert not responses.calls


class TestGetBundlePage:
    def test_defaults_count_to_bundle_default_page_size(self, session, add_page_response):
        add_page_response(ChangemakerBundle, payload=bundle([changemaker_payload()]))

        result = get_bundle_page(session, ChangemakerBundle)

        assert isinstance(result, ChangemakerBundle)
        assert result.entries[0].id == 1

    def test_forwards_page_count_content_and_extra_params(self, session, add_page_response):
        add_page_response(
            ChangemakerBundle,
            payload=bundle([]),
            page=2,
            count_per_page=25,
            content="needle",
            extra_params={"isCollaborative": "true"},
        )

        result = get_bundle_page(
            session,
            ChangemakerBundle,
            page=2,
            count_per_page=25,
            content="needle",
            extra_params={"isCollaborative": "true"},
        )

        assert result.entries == []

    def test_formats_endpoint_with_path_params(self, session, add_page_response):
        add_page_response(
            FunderCollaborativeMemberBundle,
            payload=bundle([]),
            path_params={"funder_collaborative_short_code": "acme"},
        )

        result = get_bundle_page(
            session,
            FunderCollaborativeMemberBundle,
            path_params={"funder_collaborative_short_code": "acme"},
        )

        assert result.total == 0
