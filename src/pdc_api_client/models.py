from datetime import datetime
from typing import ClassVar

from pydantic import Field

from pdc_api_client import _generated
from pdc_api_client._base import BaseSchema, PageableBundle
from pdc_api_client._generated import (
    ApplicationForm as ChangemakerApplicationForm,
)
from pdc_api_client._generated import (
    ApplicationFormField,
    BaseField,
    BaseFieldCategory,
    BaseFieldLocalization,
    Changemaker,
    ChangemakerFieldValue,
    ChangemakerFieldValueBatch,
    ChangemakerProposal,
    DataProvider,
    File,
    Funder,
    FunderCollaborativeMember,
    Initiative,
    InitiativeFieldValue,
    Opportunity,
    Organization,
    PermissionGrantEntityType,
    PermissionGrantGranteeType,
    PermissionGrantVerb,
    PresignedPost,
    Proposal,
    ProposalFieldValue,
    ProposalVersion,
    S3Bucket,
    SensitivityClassification,
    ShallowChangemaker,
    Source,
)
from pdc_api_client._generated import (
    ApplicationFormFieldInputType as InputType,
)
from pdc_api_client._generated import (
    DataType as BaseFieldDataType,
)

__all__ = [
    "ApplicationFormField",
    "BaseField",
    "BaseFieldCategory",
    "BaseFieldDataType",
    "BaseFieldLocalization",
    "BaseSchema",
    "Changemaker",
    "ChangemakerApplicationForm",
    "ChangemakerBundle",
    "ChangemakerFieldValue",
    "ChangemakerFieldValueBatch",
    "ChangemakerProposal",
    "ChangemakerProposalBundle",
    "DataProvider",
    "File",
    "Funder",
    "FunderBundle",
    "FunderCollaborativeMember",
    "FunderCollaborativeMemberBundle",
    "Initiative",
    "InitiativeBundle",
    "InitiativeFieldValue",
    "InputType",
    "NewProposalFieldValue",
    "NewProposalVersion",
    "Opportunity",
    "OpportunityBundle",
    "Organization",
    "PermissionGrantEntityType",
    "PermissionGrantGranteeType",
    "PermissionGrantVerb",
    "PresignedPost",
    "Proposal",
    "ProposalBundle",
    "ProposalFieldValue",
    "ProposalVersion",
    "S3Bucket",
    "SensitivityClassification",
    "ShallowChangemaker",
    "Source",
]


class ChangemakerBundle(_generated.ChangemakerBundle, PageableBundle):
    pdc_endpoint: ClassVar[str] = "changemakers"
    default_page_size: ClassVar[int] = 10


class FunderBundle(_generated.FunderBundle, PageableBundle):
    pdc_endpoint: ClassVar[str] = "funders"
    default_page_size: ClassVar[int] = 10


class FunderCollaborativeMemberBundle(_generated.FunderCollaborativeMemberBundle, PageableBundle):
    pdc_endpoint: ClassVar[str] = "funders/{funder_collaborative_short_code}/members"
    default_page_size: ClassVar[int] = 50


class ProposalBundle(_generated.ProposalBundle, PageableBundle):
    pdc_endpoint: ClassVar[str] = "proposals"
    default_page_size: ClassVar[int] = 10


class InitiativeBundle(_generated.InitiativeBundle, PageableBundle):
    pdc_endpoint: ClassVar[str] = "initiatives"
    default_page_size: ClassVar[int] = 10


class OpportunityBundle(_generated.OpportunityBundle, PageableBundle):
    pdc_endpoint: ClassVar[str] = "opportunities"
    default_page_size: ClassVar[int] = 10


ChangemakerProposalBundle = _generated.ChangemakerProposalBundle


# The spec defines these only as inline request bodies, so codegen does not emit them.
class NewProposalFieldValue(BaseSchema):
    application_form_field_id: int = Field(alias="applicationFormFieldId")
    position: int
    value: str
    good_as_of: datetime | None = Field(None, alias="goodAsOf")


class NewProposalVersion(BaseSchema):
    proposal_id: int = Field(alias="proposalId")
    source_id: int = Field(alias="sourceId")
    application_form_id: int = Field(alias="applicationFormId")
    field_values: list[NewProposalFieldValue] = Field(alias="fieldValues")
