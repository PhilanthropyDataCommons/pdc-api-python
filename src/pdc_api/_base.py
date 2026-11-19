from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    # Ignore undeclared fields so a field PDC adds to a response doesn't break parsing.
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
