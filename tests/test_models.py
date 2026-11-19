from pdc_api import _generated
from pdc_api.models import Funder, InitiativeFieldValue
from pdc_api.testing import funder_payload, initiative_field_value_payload


class TestFunder:
    def test_parses_nullable_id_reference_as_int(self):
        funder = Funder.model_validate(funder_payload() | {"defaultTerminologySetId": 17})

        assert funder.default_terminology_set_id == 17


class TestInitiativeFieldValue:
    def test_accepts_null_is_valid(self):
        field_value = InitiativeFieldValue.model_validate(initiative_field_value_payload() | {"isValid": None})

        assert field_value.is_valid is None


class TestGeneratedModels:
    def test_leave_permission_grants_to_the_hand_written_union(self):
        generated = {name for name in vars(_generated) if "PermissionGrant" in name}

        assert generated == {"PermissionGrantEntityType", "PermissionGrantGranteeType", "PermissionGrantVerb"}
