import uuid

import pytest

from pdc_api_client.client import get_application_form
from pdc_api_client.errors import PDCBadRequestError
from pdc_api_client.models import ChangemakerApplicationForm
from pdc_api_client.seeding.pdc_entities import seed_application_form, seed_base_field, seed_opportunity

SPEC_ENUM_VALUES = ["shortText", "longText", "radio", "dropdown", "multiselect", "hidden"]

NON_ENUM_VALUES = ["options", "multiSelect", "file"]


@pytest.fixture(scope="module")
def post_form_field(api_session):
    opportunity = seed_opportunity(api_session)
    base_field = seed_base_field(api_session)

    def _post(input_type):
        body = {
            "opportunityId": opportunity.id,
            "name": f"InputType Contract {uuid.uuid4().hex[:8]}",
            "fields": [
                {
                    "baseFieldShortCode": base_field.short_code,
                    "position": 1,
                    "label": "Contract probe",
                    "instructions": None,
                    "inputType": input_type,
                }
            ],
        }
        response = api_session.post("/applicationForms", json=body)
        return response.json()["fields"][0]["inputType"]

    return _post


class TestApplicationFormInputTypeContract:
    @pytest.mark.parametrize("value", SPEC_ENUM_VALUES)
    def test_spec_enum_value_round_trips(self, post_form_field, value):
        assert post_form_field(value) == value

    def test_null_input_type_round_trips(self, post_form_field):
        assert post_form_field(None) is None

    @pytest.mark.parametrize("value", NON_ENUM_VALUES)
    def test_non_enum_value_is_rejected(self, post_form_field, value):
        with pytest.raises(PDCBadRequestError):
            post_form_field(value)

    def test_field_without_input_type_parses_as_none(self, api_session):
        opportunity = seed_opportunity(api_session)
        base_field = seed_base_field(api_session)
        seeded = seed_application_form(
            api_session,
            opportunity=opportunity,
            base_field_short_codes=[base_field.short_code],
        )

        form = get_application_form(api_session, application_form_id=seeded.id)

        assert isinstance(form, ChangemakerApplicationForm)
        assert form.fields[0].input_type is None
