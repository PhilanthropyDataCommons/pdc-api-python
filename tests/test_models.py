from pdc_api_client import _generated
from pdc_api_client.models import Funder, InitiativeFieldValue
from pdc_api_client.testing import funder_payload, initiative_field_value_payload


def test_nullable_id_reference_is_a_plain_int():
    funder = Funder.model_validate(funder_payload() | {"defaultTerminologySetId": 17})

    assert funder.default_terminology_set_id == 17


def test_field_value_with_null_is_valid_parses():
    field_value = InitiativeFieldValue.model_validate(initiative_field_value_payload() | {"isValid": None})

    assert field_value.is_valid is None


def test_generated_models_leave_permission_grants_to_the_hand_written_union():
    generated = {name for name in vars(_generated) if "PermissionGrant" in name}

    assert generated == {"PermissionGrantEntityType", "PermissionGrantGranteeType", "PermissionGrantVerb"}
