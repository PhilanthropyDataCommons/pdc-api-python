from pdc_api.client import get_changemaker_proposals
from pdc_api.seeding.pdc_entities import (
    SeededChangemakerWithProposals,
    SeededProposalBundle,
    seed_application_form,
    seed_base_field,
    seed_changemaker,
    seed_changemaker_with_proposals,
    seed_data_provider,
    seed_funder,
    seed_opportunity,
    seed_proposal,
    seed_proposal_bundle,
    seed_source,
)


class TestSeedIndividualEntities:
    def test_seed_base_field(self, api_session):
        bf = seed_base_field(api_session)
        assert bf.short_code
        assert bf.label

    def test_seed_funder(self, api_session):
        funder = seed_funder(api_session)
        assert funder.short_code
        assert funder.name

    def test_seed_changemaker(self, api_session):
        cm = seed_changemaker(api_session)
        assert cm.id > 0
        assert cm.name

    def test_seed_opportunity(self, api_session):
        opp = seed_opportunity(api_session)
        assert opp.id > 0
        assert opp.title
        assert opp.funder is not None

    def test_seed_data_provider(self, api_session):
        dp = seed_data_provider(api_session)
        assert dp.short_code
        assert dp.name

    def test_seed_source(self, api_session):
        source = seed_source(api_session)
        assert source.id > 0
        assert source.label

    def test_seed_source_for_changemaker(self, api_session):
        cm = seed_changemaker(api_session)
        source = seed_source(api_session, changemaker_id=cm.id)
        assert source.id > 0

    def test_seed_application_form(self, api_session):
        bf = seed_base_field(api_session)
        form = seed_application_form(
            api_session,
            base_field_short_codes=[bf.short_code],
        )
        assert form.id > 0
        assert len(form.fields) == 1

    def test_seed_proposal(self, api_session):
        proposal = seed_proposal(api_session)
        assert proposal.id > 0
        assert proposal.external_id


class TestSeedProposalBundle:
    def test_creates_complete_bundle(self, api_session):
        bundle = seed_proposal_bundle(api_session)
        assert isinstance(bundle, SeededProposalBundle)
        assert bundle.changemaker is not None
        assert bundle.changemaker.id > 0
        assert bundle.funder.short_code
        assert bundle.opportunity.id > 0
        assert bundle.source.id > 0
        assert bundle.application_form.id > 0
        assert bundle.proposal.id > 0
        assert bundle.proposal_version.id > 0

    def test_bundle_seeds_standard_proposal_fields(self, api_session):
        bundle = seed_proposal_bundle(api_session)
        seeded_values = {
            fv.application_form_field.base_field.short_code: fv.value for fv in bundle.proposal_version.field_values
        }
        assert seeded_values["proposal_name"]
        assert seeded_values["proposal_summary"]
        assert seeded_values["proposal_focus"]
        assert seeded_values["proposal_date"]

    def test_bundle_is_retrievable(self, api_session):
        bundle = seed_proposal_bundle(api_session)
        assert bundle.changemaker is not None
        results = list(
            get_changemaker_proposals(
                api_session,
                changemaker_id=bundle.changemaker.id,
            )
        )
        assert len(results) == 1
        assert results[0].proposal_id == bundle.proposal.id


class TestSeedChangemakerWithProposals:
    def test_links_every_proposal_to_one_changemaker(self, api_session):
        result = seed_changemaker_with_proposals(api_session, proposal_count=2)
        assert isinstance(result, SeededChangemakerWithProposals)
        assert len(result.bundles) == 2
        assert len({b.proposal.id for b in result.bundles}) == 2

        linked = list(
            get_changemaker_proposals(
                api_session,
                changemaker_id=result.changemaker.id,
            )
        )
        assert len(linked) == 2

    def test_seed_proposal_corpus_produces_varied_bundles(self, seeded_pdc_corpus):
        assert len(seeded_pdc_corpus) >= 1
        assert all(isinstance(b, SeededProposalBundle) for b in seeded_pdc_corpus)
