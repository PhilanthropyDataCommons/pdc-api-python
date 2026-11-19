import uuid
from datetime import UTC, datetime
from http import HTTPStatus

import pytest
import requests

from pdc_api_client.client import (
    create_changemaker_field_value,
    create_changemaker_field_value_batch,
    create_changemaker_source,
    create_initiative,
    create_initiative_field_value,
    create_proposal,
    create_proposal_version,
    get_application_form,
    get_application_form_by_name,
    get_base_fields,
    get_bundle_page,
    get_changemaker,
    get_changemaker_field_values,
    get_changemaker_proposals,
    get_changemakers,
    get_data_providers,
    get_funder,
    get_funders,
    get_initiative,
    get_initiative_field_values,
    get_initiatives,
    get_organization_by_keycloak_id,
    get_proposal,
    get_proposals,
    link_changemaker_to_proposal,
)
from pdc_api_client.errors import PDCNotFoundError, ProposalNotFoundError
from pdc_api_client.models import (
    BaseField,
    Changemaker,
    ChangemakerApplicationForm,
    ChangemakerBundle,
    ChangemakerProposal,
    DataProvider,
    Funder,
    FunderBundle,
    FunderCollaborativeMember,
    FunderCollaborativeMemberBundle,
    Initiative,
    InitiativeBundle,
    InitiativeFieldValue,
    NewProposalFieldValue,
    NewProposalVersion,
    OpportunityBundle,
    Proposal,
    ProposalBundle,
)
from pdc_api_client.seeding.pdc_entities import (
    seed_application_form,
    seed_base_field,
    seed_changemaker,
    seed_data_provider,
    seed_funder,
    seed_funder_collaborative_member,
    seed_initiative,
    seed_initiative_field_value,
    seed_opportunity,
    seed_source,
)


class TestAuthentication:
    def test_unauthenticated_request_is_rejected(self, api_session):
        raw_url = api_session._make_api_url("/users")
        r = requests.get(raw_url, timeout=10)
        assert r.status_code == HTTPStatus.UNAUTHORIZED

    def test_authenticated_request_succeeds(self, api_session):
        response = api_session.get("/users")
        assert response.status_code == HTTPStatus.OK
        assert "total" in response.json()


class TestBaseFields:
    def test_get_basefields_returns_list(self, api_session):
        result = list(get_base_fields(api_session))
        assert len(result) > 0

    def test_seeded_base_field_exists(self, api_session, seeded_pdc_stack):
        result = list(get_base_fields(api_session))
        short_codes = [bf.short_code for bf in result]
        assert seeded_pdc_stack.application_form.fields[0]["baseFieldShortCode"] in short_codes

    def test_base_field_parses_as_pydantic_model(self, api_session):
        result = list(get_base_fields(api_session))
        bf = result[0]
        assert isinstance(bf, BaseField)
        assert bf.short_code
        assert bf.label

    def test_basefields_endpoint_returns_paginated_bundle(self, api_session):
        response = api_session.get("/baseFields", params={"_page": 1, "_count": 5})

        assert response.status_code == HTTPStatus.OK
        payload = response.json()

        assert "entries" in payload
        assert "total" in payload
        assert len(payload["entries"]) <= 5


class TestFunders:
    def test_get_funders_returns_entries(self, api_session):
        result = list(get_funders(api_session))
        assert len(result) > 0

    def test_get_funder_by_shortcode(self, api_session, seeded_pdc_stack):
        funder = get_funder(api_session, short_code=seeded_pdc_stack.funder.short_code)
        assert isinstance(funder, Funder)
        assert funder.short_code == seeded_pdc_stack.funder.short_code
        assert funder.name == seeded_pdc_stack.funder.name

    def test_get_page_returns_funder_bundle(self, api_session):
        bundle = get_bundle_page(api_session, FunderBundle, page=1, count_per_page=5)
        assert isinstance(bundle, FunderBundle)
        assert bundle.total >= 1
        assert all(isinstance(entry, Funder) for entry in bundle.entries)


class TestFunderCollaboratives:
    def test_get_funder_parses_collaborative_flag(self, api_session):
        collaborative = seed_funder(api_session, is_collaborative=True)

        funder = get_funder(api_session, short_code=collaborative.short_code)

        assert isinstance(funder, Funder)
        assert funder.short_code == collaborative.short_code
        assert funder.is_collaborative is True

    def test_is_collaborative_filter_returns_only_collaboratives(self, api_session):
        collaborative = seed_funder(api_session, is_collaborative=True)
        regular = seed_funder(api_session, is_collaborative=False)

        bundle = get_bundle_page(
            api_session,
            FunderBundle,
            page=1,
            count_per_page=100,
            extra_params={"isCollaborative": "true"},
        )

        short_codes = {entry.short_code for entry in bundle.entries}
        assert collaborative.short_code in short_codes
        assert regular.short_code not in short_codes
        assert all(entry.is_collaborative is True for entry in bundle.entries)

    def test_search_combined_with_is_collaborative_filter(self, api_session, suffix):
        marker = f"inttest-combo-{suffix}"
        matching_collab = seed_funder(
            api_session,
            name=f"{marker} Funders Collaborative",
            is_collaborative=True,
        )
        non_matching_collab = seed_funder(api_session, is_collaborative=True)
        matching_regular = seed_funder(
            api_session,
            name=f"{marker} Foundation",
            is_collaborative=False,
        )

        bundle = get_bundle_page(
            api_session,
            FunderBundle,
            page=1,
            count_per_page=100,
            content=marker,
            extra_params={"isCollaborative": "true"},
        )

        short_codes = {entry.short_code for entry in bundle.entries}
        assert matching_collab.short_code in short_codes
        assert non_matching_collab.short_code not in short_codes
        assert matching_regular.short_code not in short_codes
        assert all(entry.is_collaborative is True for entry in bundle.entries)

    def test_pagination_with_is_collaborative_filter(self, api_session, suffix):
        marker = f"inttest-page-{suffix}"
        collaboratives = [
            seed_funder(
                api_session,
                name=f"{marker} Collaborative {i}",
                is_collaborative=True,
            )
            for i in range(3)
        ]
        # A matching non-collaborative that the filter must exclude from `total`.
        seed_funder(
            api_session,
            name=f"{marker} Foundation",
            is_collaborative=False,
        )

        page_one = get_bundle_page(
            api_session,
            FunderBundle,
            page=1,
            count_per_page=2,
            content=marker,
            extra_params={"isCollaborative": "true"},
        )
        page_two = get_bundle_page(
            api_session,
            FunderBundle,
            page=2,
            count_per_page=2,
            content=marker,
            extra_params={"isCollaborative": "true"},
        )

        assert page_one.total == len(collaboratives)
        assert page_two.total == len(collaboratives)
        assert len(page_one.entries) == 2
        assert len(page_two.entries) == 1
        seen = {entry.short_code for entry in page_one.entries + page_two.entries}
        assert seen == {c.short_code for c in collaboratives}
        assert all(entry.is_collaborative is True for entry in page_one.entries + page_two.entries)

    def test_is_collaborative_false_filter_excludes_collaboratives(self, api_session):
        collaborative = seed_funder(api_session, is_collaborative=True)
        regular = seed_funder(api_session, is_collaborative=False)

        bundle = get_bundle_page(
            api_session,
            FunderBundle,
            page=1,
            count_per_page=100,
            extra_params={"isCollaborative": "false"},
        )

        short_codes = {entry.short_code for entry in bundle.entries}
        assert regular.short_code in short_codes
        assert collaborative.short_code not in short_codes
        assert all(entry.is_collaborative is not True for entry in bundle.entries)

    def test_get_funder_collaborative_members_returns_seeded_members(self, api_session):
        collaborative = seed_funder(api_session, is_collaborative=True)
        members = [seed_funder(api_session, is_collaborative=False) for _ in range(2)]
        for member in members:
            seed_funder_collaborative_member(api_session, collaborative=collaborative, member=member)

        bundle = get_bundle_page(
            api_session,
            FunderCollaborativeMemberBundle,
            path_params={"funder_collaborative_short_code": collaborative.short_code},
        )

        assert bundle.total == len(members)
        assert all(isinstance(entry, FunderCollaborativeMember) for entry in bundle.entries)
        member_short_codes = {entry.member_funder_short_code for entry in bundle.entries}
        assert {m.short_code for m in members} <= member_short_codes
        assert all(entry.funder_collaborative_short_code == collaborative.short_code for entry in bundle.entries)

    def test_get_funder_collaborative_members_paginates(self, api_session):
        collaborative = seed_funder(api_session, is_collaborative=True)
        members = [seed_funder(api_session, is_collaborative=False) for _ in range(3)]
        for member in members:
            seed_funder_collaborative_member(api_session, collaborative=collaborative, member=member)

        page_one = get_bundle_page(
            api_session,
            FunderCollaborativeMemberBundle,
            page=1,
            count_per_page=2,
            path_params={"funder_collaborative_short_code": collaborative.short_code},
        )
        page_two = get_bundle_page(
            api_session,
            FunderCollaborativeMemberBundle,
            page=2,
            count_per_page=2,
            path_params={"funder_collaborative_short_code": collaborative.short_code},
        )

        assert page_one.total == len(members)
        assert page_two.total == len(members)
        assert len(page_one.entries) == 2
        assert len(page_two.entries) == 1

        seen = {entry.member_funder_short_code for entry in page_one.entries + page_two.entries}
        assert seen == {m.short_code for m in members}

    def test_members_paginate_at_default_page_size_boundary(
        self,
        api_session,
        seeded_large_collaborative,
    ):
        page_size = FunderCollaborativeMemberBundle.default_page_size
        expected_total = page_size + 1
        path_params = {"funder_collaborative_short_code": seeded_large_collaborative.collaborative.short_code}

        page_one = get_bundle_page(
            api_session,
            FunderCollaborativeMemberBundle,
            page=1,
            path_params=path_params,
        )
        page_two = get_bundle_page(
            api_session,
            FunderCollaborativeMemberBundle,
            page=2,
            path_params=path_params,
        )

        assert page_one.total == expected_total
        assert len(page_one.entries) == page_size
        assert len(page_two.entries) == 1

        seeded_short_codes = {m.short_code for m in seeded_large_collaborative.members}
        seen = {entry.member_funder_short_code for entry in page_one.entries + page_two.entries}
        assert seen == seeded_short_codes


class TestOpportunities:
    def test_funder_filter_returns_only_that_funders_opportunities(self, api_session):
        funder = seed_funder(api_session)
        other_funder = seed_funder(api_session)
        mine = seed_opportunity(api_session, funder=funder)
        theirs = seed_opportunity(api_session, funder=other_funder)

        bundle = get_bundle_page(
            api_session,
            OpportunityBundle,
            page=1,
            count_per_page=100,
            extra_params={"funder": funder.short_code},
        )

        ids = {entry.id for entry in bundle.entries}
        assert mine.id in ids
        assert theirs.id not in ids
        assert all(entry.funder_short_code == funder.short_code for entry in bundle.entries)


class TestDataProviders:
    def test_seeded_data_provider_in_list(self, api_session):
        seeded = seed_data_provider(api_session)

        result = list(get_data_providers(api_session))

        assert all(isinstance(dp, DataProvider) for dp in result)
        assert seeded.short_code in {dp.short_code for dp in result}


class TestChangemakers:
    def test_get_changemakers_returns_entries(self, api_session):
        result = list(get_changemakers(api_session))
        assert len(result) > 0

    def test_seeded_changemaker_in_list(self, api_session, seeded_pdc_stack):
        result = list(get_changemakers(api_session))
        ids = [cm.id for cm in result]
        assert seeded_pdc_stack.changemaker.id in ids

    def test_get_changemaker_by_id(self, api_session, seeded_pdc_stack):
        expected = seeded_pdc_stack.changemaker
        cm = get_changemaker(api_session, changemaker_id=expected.id)
        assert isinstance(cm, Changemaker)
        assert cm.id == expected.id
        assert cm.name == expected.name

    def test_get_page_returns_changemaker_bundle(self, api_session):
        bundle = get_bundle_page(api_session, ChangemakerBundle, page=1, count_per_page=5)
        assert isinstance(bundle, ChangemakerBundle)
        assert bundle.total >= 1
        assert all(isinstance(entry, Changemaker) for entry in bundle.entries)


class TestChangemakerFieldValueWrites:
    def test_changemaker_sourced_batch_round_trips(self, api_session):
        changemaker = seed_changemaker(api_session)
        base_field = seed_base_field(api_session, category="organization")
        good_as_of = datetime(2026, 1, 31, 9, 0, tzinfo=UTC)

        source = create_changemaker_source(api_session, changemaker_id=changemaker.id, label="Self-reported")
        batch = create_changemaker_field_value_batch(api_session, source_id=source.id, notes="Edited")
        create_changemaker_field_value(
            api_session,
            changemaker_id=changemaker.id,
            base_field_short_code=base_field.short_code,
            batch_id=batch.id,
            value="Springfield",
            good_as_of=good_as_of,
        )

        [stored] = get_changemaker_field_values(api_session, batch_id=batch.id)
        assert batch.source_id == source.id
        assert (stored.changemaker_id, stored.base_field_short_code, stored.value, stored.good_as_of) == (
            changemaker.id,
            base_field.short_code,
            "Springfield",
            good_as_of,
        )


class TestProposals:
    def test_get_changemaker_proposals_by_changemaker_id(self, api_session, seeded_pdc_stack):
        result = list(
            get_changemaker_proposals(
                api_session,
                changemaker_id=seeded_pdc_stack.changemaker.id,
            )
        )
        assert len(result) == 1
        cp = result[0]
        assert isinstance(cp, ChangemakerProposal)
        assert cp.changemaker_id == seeded_pdc_stack.changemaker.id
        assert cp.proposal_id == seeded_pdc_stack.proposal.id

    def test_get_changemaker_proposal_by_proposal_id(self, api_session, seeded_pdc_stack):
        result = list(
            get_changemaker_proposals(
                api_session,
                proposal_id=seeded_pdc_stack.proposal.id,
            )
        )
        assert len(result) == 1
        cp = result[0]
        assert isinstance(cp, ChangemakerProposal)
        assert cp.proposal_id == seeded_pdc_stack.proposal.id
        assert cp.changemaker_id == seeded_pdc_stack.changemaker.id

    def test_proposal_has_versions(self, api_session, seeded_pdc_stack):
        result = list(
            get_changemaker_proposals(
                api_session,
                proposal_id=seeded_pdc_stack.proposal.id,
            )
        )
        assert len(result[0].proposal.versions) >= 1

    def test_get_proposal_by_id(self, api_session, seeded_pdc_stack):
        expected = seeded_pdc_stack.proposal
        proposal = get_proposal(api_session, proposal_id=expected.id)
        assert isinstance(proposal, Proposal)
        assert proposal.id == expected.id
        assert proposal.external_id == expected.external_id
        assert len(proposal.versions) >= 1

    def test_get_proposal_404_raises_proposal_not_found(self, api_session):
        with pytest.raises(ProposalNotFoundError):
            get_proposal(api_session, proposal_id=999999999)

    def test_get_page_returns_proposal_bundle(self, api_session):
        bundle = get_bundle_page(api_session, ProposalBundle, page=1, count_per_page=5)
        assert isinstance(bundle, ProposalBundle)
        assert bundle.total >= 1
        assert all(isinstance(entry, Proposal) for entry in bundle.entries)

    def test_get_proposals_includes_field_values(self, api_session, seeded_pdc_stack):
        proposals = {p.id: p for p in get_proposals(api_session, count_per_page=5)}

        [version] = proposals[seeded_pdc_stack.proposal.id].versions
        assert version.field_values


class TestInitiatives:
    def test_get_initiatives_includes_seeded_initiative(self, api_session, seeded_pdc_stack):
        initiative = seed_initiative(api_session, changemaker_id=seeded_pdc_stack.changemaker.id)

        initiatives = list(get_initiatives(api_session))

        assert all(isinstance(i, Initiative) for i in initiatives)
        assert initiative.id in {i.id for i in initiatives}

    def test_get_initiative(self, api_session, seeded_pdc_stack):
        seeded = seed_initiative(api_session, changemaker_id=seeded_pdc_stack.changemaker.id)

        assert get_initiative(api_session, initiative_id=seeded.id) == seeded

    def test_bundle_page_filters_by_changemaker(self, api_session, seeded_pdc_stack):
        other_changemaker = seed_changemaker(api_session)
        seeded = seed_initiative(api_session, changemaker_id=seeded_pdc_stack.changemaker.id)
        seed_initiative(api_session, changemaker_id=other_changemaker.id)

        bundle = get_bundle_page(
            api_session, InitiativeBundle, extra_params={"changemaker": seeded_pdc_stack.changemaker.id}
        )

        assert seeded.id in {i.id for i in bundle.entries}
        assert {i.changemaker_id for i in bundle.entries} == {seeded_pdc_stack.changemaker.id}

    def test_get_initiative_field_values(self, api_session, seeded_pdc_stack):
        initiative = seed_initiative(api_session, changemaker_id=seeded_pdc_stack.changemaker.id)
        short_code = seeded_pdc_stack.application_form.fields[0]["baseFieldShortCode"]
        seed_initiative_field_value(
            api_session,
            initiative_id=initiative.id,
            base_field_short_code=short_code,
            source=seeded_pdc_stack.source,
            value="Clean water",
        )

        [field_value] = get_initiative_field_values(api_session, initiative_id=initiative.id)

        assert isinstance(field_value, InitiativeFieldValue)
        assert (field_value.base_field_short_code, field_value.value) == (short_code, "Clean water")

    def test_create_initiative_with_a_field_value(self, api_session, seeded_pdc_stack):
        short_code = seeded_pdc_stack.application_form.fields[0]["baseFieldShortCode"]
        good_as_of = datetime(2026, 1, 31, 9, 0, tzinfo=UTC)

        initiative = create_initiative(api_session, changemaker_id=seeded_pdc_stack.changemaker.id, title="Clean water")
        create_initiative_field_value(
            api_session,
            initiative_id=initiative.id,
            base_field_short_code=short_code,
            value="Wells for the valley",
            source_id=seeded_pdc_stack.source.id,
            good_as_of=good_as_of,
        )

        assert get_initiative(api_session, initiative_id=initiative.id).title == "Clean water"
        [field_value] = get_initiative_field_values(api_session, initiative_id=initiative.id)
        assert (field_value.base_field_short_code, field_value.value, field_value.good_as_of) == (
            short_code,
            "Wells for the valley",
            good_as_of,
        )


class TestOrganizations:
    def test_get_organization_by_keycloak_id_404(self, api_session):
        with pytest.raises(PDCNotFoundError):
            get_organization_by_keycloak_id(api_session, keycloak_id=str(uuid.uuid4()))


class TestApplicationForm:
    def test_get_application_form_returns_seeded_form(self, api_session):
        opportunity = seed_opportunity(api_session)
        base_field = seed_base_field(api_session)
        seeded_form = seed_application_form(
            api_session,
            opportunity=opportunity,
            base_field_short_codes=[base_field.short_code],
        )

        form = get_application_form(api_session, application_form_id=seeded_form.id)

        assert isinstance(form, ChangemakerApplicationForm)
        assert form.id == seeded_form.id
        assert form.opportunity_id == opportunity.id
        assert {f.base_field.short_code for f in form.fields} == {base_field.short_code}

    def test_get_application_form_by_name_finds_seeded_form(self, api_session, suffix):
        name = f"Named form {suffix}"
        seeded_form = seed_application_form(api_session, name=name)

        assert get_application_form_by_name(api_session, name=name).id == seeded_form.id


class TestProposalCreationFlow:
    def test_create_proposal_link_and_round_trip(self, api_session, suffix):
        funder = seed_funder(api_session)
        opportunity = seed_opportunity(api_session, funder=funder)
        source = seed_source(api_session, funder_short_code=funder.short_code)
        base_field = seed_base_field(api_session)
        application_form = seed_application_form(
            api_session,
            opportunity=opportunity,
            base_field_short_codes=[base_field.short_code],
        )
        application_form_field_id = application_form.fields[0]["id"]
        changemaker = seed_changemaker(api_session)

        proposal = create_proposal(
            api_session,
            data={
                "opportunityId": opportunity.id,
                "externalId": f"inttest-{suffix}",
            },
        )

        proposal_version = create_proposal_version(
            api_session,
            proposal_version=NewProposalVersion(
                proposal_id=proposal.id,
                source_id=source.id,
                application_form_id=application_form.id,
                field_values=[
                    NewProposalFieldValue(
                        application_form_field_id=application_form_field_id,
                        position=1,
                        value="Round-trip test value",
                    )
                ],
            ),
        )
        link = link_changemaker_to_proposal(
            api_session,
            changemaker_id=changemaker.id,
            proposal_id=proposal.id,
        )

        assert proposal_version.proposal_id == proposal.id
        assert link.changemaker_id == changemaker.id
        assert link.proposal_id == proposal.id

        roundtrip = get_proposal(api_session, proposal_id=proposal.id)
        assert roundtrip.id == proposal.id
        assert any(v.id == proposal_version.id for v in roundtrip.versions)
        assert changemaker.id in {cm.id for cm in roundtrip.changemakers}
