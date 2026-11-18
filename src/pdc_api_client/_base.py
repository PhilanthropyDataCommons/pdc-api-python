from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    # Ignore undeclared fields so a field PDC adds to a response doesn't break parsing.
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class PageableBundle(BaseSchema):
    pdc_endpoint: ClassVar[str]
    default_page_size: ClassVar[int]
