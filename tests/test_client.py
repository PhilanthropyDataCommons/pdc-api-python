import pytest

from pdc_api_client import errors
from pdc_api_client.client import (
    _iterate_pages,
    get_basefields,
    get_changemaker_field_value_batch,
    get_changemaker_field_values,
    get_changemaker_proposals,
    get_changemakers,
    get_data_providers,
    get_funders,
    get_initiatives,
)
from pdc_api_client.models import (
    BaseFieldDataType,
    Changemaker,
    ChangemakerFieldValue,
    ChangemakerFieldValueBatch,
    ChangemakerProposal,
    DataProvider,
    Funder,
)
from pdc_api_client.testing import (
    base_field_payload as _basefield,
)
from pdc_api_client.testing import (
    bundle,
    changemaker_field_value_batch_payload,
    changemaker_field_value_payload,
    changemaker_payload,
    changemaker_proposal_payload,
    data_provider_payload,
    funder_payload,
    initiative_payload,
)


class TestGetBasefields:
    # PDC sorts /baseFields only by created_at, which ties, so paging can repeat or skip fields.
    def test_fetches_every_field_in_one_page(self, session, add_json_response):
        payload = {"entries": [_basefield(f"f{i}") for i in range(75)], "total": 75}
        add_json_response(path="/baseFields", payload=payload, query_params={"_page": 1, "_count": 10_000})

        result = get_basefields(session)

        assert [b.short_code for b in result] == [f"f{i}" for i in range(75)]

    def test_validates_date_and_date_time_data_types(self, session, add_json_response):
        payload = {"entries": [_basefield("d", data_type="date"), _basefield("dt", data_type="date_time")], "total": 2}
        add_json_response(path="/baseFields", payload=payload, query_params={"_page": 1, "_count": 10_000})

        result = get_basefields(session)

        assert [b.data_type for b in result] == [BaseFieldDataType.DATE, BaseFieldDataType.DATE_TIME]


class TestGetChangemakers:
    def test_yields_validated_models_across_pages(self, session, add_json_response):
        page_1 = bundle([changemaker_payload(id=i) for i in range(1, 51)], total=60)
        page_2 = bundle([changemaker_payload(id=50 + i) for i in range(1, 11)], total=60)
        add_json_response(path="/changemakers", payload=page_1, query_params={"_page": 1, "_count": 50})
        add_json_response(path="/changemakers", payload=page_2, query_params={"_page": 2, "_count": 50})

        result = list(get_changemakers(session))

        assert all(isinstance(c, Changemaker) for c in result)
        assert [c.id for c in result] == list(range(1, 61))


class TestGetFunders:
    def test_yields_validated_models(self, session, add_json_response):
        payload = bundle([funder_payload(short_code="a"), funder_payload(short_code="b")])
        add_json_response(path="/funders", payload=payload, query_params={"_page": 1, "_count": 50})

        result = list(get_funders(session))

        assert all(isinstance(f, Funder) for f in result)
        assert [f.short_code for f in result] == ["a", "b"]


class TestGetDataProviders:
    def test_yields_validated_models(self, session, add_json_response):
        payload = bundle(
            [
                data_provider_payload(short_code="charity_nav", name="Charity Navigator"),
                data_provider_payload(short_code="art_for_change", name="Art For Change"),
            ]
        )
        add_json_response(path="/dataProviders", payload=payload, query_params={"_page": 1, "_count": 50})

        result = list(get_data_providers(session))

        assert all(isinstance(dp, DataProvider) for dp in result)
        assert [dp.short_code for dp in result] == ["charity_nav", "art_for_change"]


class TestGetChangemakerProposals:
    def test_yields_validated_models(self, session, add_json_response):
        payload = bundle([changemaker_proposal_payload(id=1), changemaker_proposal_payload(id=2)])
        add_json_response(path="/changemakerProposals", payload=payload, query_params={"_page": 1, "_count": 50})

        result = list(get_changemaker_proposals(session))

        assert all(isinstance(cp, ChangemakerProposal) for cp in result)
        assert [cp.id for cp in result] == [1, 2]

    def test_forwards_changemaker_and_proposal_filters(self, session, add_json_response):
        payload = bundle([changemaker_proposal_payload()])
        add_json_response(
            path="/changemakerProposals",
            payload=payload,
            query_params={"_page": 1, "_count": 50, "changemaker": 10, "proposal": 100},
        )

        result = list(get_changemaker_proposals(session, changemaker_id=10, proposal_id=100))

        assert [cp.id for cp in result] == [1]

    def test_count_per_page_overrides_default_page_size(self, session, add_json_response):
        payload = bundle([changemaker_proposal_payload(id=1)])
        add_json_response(
            path="/changemakerProposals",
            payload=payload,
            query_params={"_page": 1, "_count": 10},
        )

        result = list(get_changemaker_proposals(session, count_per_page=10))

        assert [cp.id for cp in result] == [1]


class TestGetInitiatives:
    def test_lists_every_initiative_without_a_changemaker(self, session, add_json_response):
        add_json_response(
            path="/initiatives", payload=bundle([initiative_payload()]), query_params={"_page": 1, "_count": 50}
        )

        assert [i.id for i in get_initiatives(session)] == [1]

    def test_forwards_changemaker_filter(self, session, add_json_response):
        add_json_response(
            path="/initiatives",
            payload=bundle([initiative_payload(changemaker_id=10)]),
            query_params={"_page": 1, "_count": 50, "changemaker": 10},
        )

        assert [i.id for i in get_initiatives(session, changemaker_id=10)] == [1]


class TestGetChangemakerFieldValues:
    def test_yields_validated_models(self, session, add_json_response):
        payload = bundle(
            [
                changemaker_field_value_payload(id=1, short_code="organization_name"),
                changemaker_field_value_payload(id=2, short_code="organization_mission_statement"),
            ]
        )
        add_json_response(path="/changemakerFieldValues", payload=payload, query_params={"_page": 1, "_count": 50})

        result = list(get_changemaker_field_values(session))

        assert all(isinstance(fv, ChangemakerFieldValue) for fv in result)
        assert [fv.id for fv in result] == [1, 2]
        assert result[0].batch.source.label == "src"

    def test_forwards_changemaker_and_batch_filters(self, session, add_json_response):
        payload = bundle([changemaker_field_value_payload(id=1)])
        add_json_response(
            path="/changemakerFieldValues",
            payload=payload,
            query_params={"_page": 1, "_count": 50, "changemaker": 10, "changemakerFieldValueBatch": 5},
        )

        result = list(get_changemaker_field_values(session, changemaker_id=10, batch_id=5))

        assert [fv.id for fv in result] == [1]


class TestGetChangemakerFieldValueBatch:
    def test_returns_validated_model(self, session, add_json_response):
        add_json_response(
            path="changemakerFieldValueBatches/7",
            payload=changemaker_field_value_batch_payload(id=7, notes="Charity Navigator import"),
        )

        result = get_changemaker_field_value_batch(session, batch_id=7)

        assert isinstance(result, ChangemakerFieldValueBatch)
        assert result.id == 7
        assert result.notes == "Charity Navigator import"

    def test_raises_batch_not_found_on_404(self, session, add_json_response):
        add_json_response(path="changemakerFieldValueBatches/999", payload={"detail": "not found"}, status=404)

        with pytest.raises(errors.ChangemakerFieldValueBatchNotFoundError):
            get_changemaker_field_value_batch(session, batch_id=999)


class TestIteratePages:
    def test_handles_empty_bundle(self, session, add_json_response):
        empty = {"entries": [], "total": 0}
        add_json_response(path="/things", payload=empty, query_params={"_page": 1, "_count": 50})

        pages = list(_iterate_pages(session, endpoint="/things"))

        assert pages == [empty]

    def test_walks_every_page_until_total_reached(self, session, add_json_response):
        page_1 = bundle([changemaker_payload(id=i) for i in range(50)], total=60)
        page_2 = bundle([changemaker_payload(id=50 + i) for i in range(10)], total=60)
        add_json_response(path="/things", payload=page_1, query_params={"_page": 1, "_count": 50})
        add_json_response(path="/things", payload=page_2, query_params={"_page": 2, "_count": 50})

        pages = list(_iterate_pages(session, endpoint="/things"))

        assert [p["entries"][0]["id"] for p in pages] == [0, 50]
        assert sum(len(p["entries"]) for p in pages) == 60

    def test_max_requests_caps_traversal(self, session, add_json_response):
        full = bundle([changemaker_payload(id=i) for i in range(50)], total=500)
        add_json_response(path="/things", payload=full, query_params={"_page": 1, "_count": 50})
        add_json_response(path="/things", payload=full, query_params={"_page": 2, "_count": 50})

        pages = list(_iterate_pages(session, endpoint="/things", max_requests=2))

        assert len(pages) == 2


class TestPermissionsMap:
    def test_funder_parses_unknown_scope_and_verb(self):
        funder = Funder.model_validate({**funder_payload(), "permissions": {"newScope": ["approve"]}})

        assert funder.permissions == {"newScope": ["approve"]}

    def test_changemaker_parses_unknown_scope_and_verb(self):
        changemaker = Changemaker.model_validate({**changemaker_payload(), "permissions": {"newScope": ["approve"]}})

        assert changemaker.permissions == {"newScope": ["approve"]}
