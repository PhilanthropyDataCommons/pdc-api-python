# pdc-python-client

A Python client for the [Philanthropy Data Commons](https://philanthropydatacommons.org) (PDC) API.

PDC is an access-controlled service where changemakers and funders share funding proposals and organization data. A changemaker can submit a proposal once and share it with any funder it chooses, and the data owner decides who sees what. This package wraps the [PDC API](https://api.philanthropydatacommons.org/) in typed Pydantic models, handles pagination, and raises one exception class per HTTP error. It doesn't depend on any web framework.

Install it as `pdc-python-client` and import it as `pdc_api_client`.

> **Status:** alpha. The API may change between minor versions until 1.0.

## Installation

The package is not on PyPI yet. Install it from a tagged release on GitHub:

```bash
pip install "pdc-python-client @ git+https://github.com/PhilanthropyDataCommons/pdc-python-client@v0.2.0"
```

or with uv:

```bash
uv add git+https://github.com/PhilanthropyDataCommons/pdc-python-client --tag v0.2.0
```

Two optional extras add test and seeding helpers:

- **`testing`:** helpers for mocking PDC responses in your own tests, built on [`responses`](https://github.com/getsentry/responses).
- **`seeding`:** helpers for creating PDC and Keycloak test data, built on [`python-keycloak`](https://github.com/marcospereirampj/python-keycloak) and [Faker](https://github.com/joke2k/faker).

Add them to the requirement, as in `"pdc-python-client[testing,seeding] @ git+https://github.com/PhilanthropyDataCommons/pdc-python-client@v0.2.0"`.

Python 3.12 or later is required.

## Quickstart

```python
from pdc_api_client import APISession
from pdc_api_client.client import get_changemakers, get_proposal
from pdc_api_client.token import KeycloakClientCredentialsProvider

session = APISession(
    base_url="https://api.philanthropydatacommons.org/",
    token_provider=KeycloakClientCredentialsProvider(
        server_url="https://auth.philanthropydatacommons.org",
        realm="pdc",
        client_id="your-client-id",
        client_secret="your-client-secret",
        timeout=15,
    ),
)

for changemaker in get_changemakers(session):
    print(changemaker.name, changemaker.tax_id)

proposal = get_proposal(session, proposal_id=42)
```

Every response is parsed into a model from `pdc_api_client.models`, with snake_case attributes over PDC's camelCase fields.

## Authentication

`APISession` asks a token provider for a bearer token before each request. A token provider is any object with these two methods:

```python
class TokenProvider(Protocol):
    def get_token(self) -> str: ...
    def refresh_if_necessary(self) -> None: ...
```

The package ships one: `KeycloakClientCredentialsProvider` runs the OAuth2 client-credentials grant against PDC's Keycloak and caches the token until 30 seconds before it expires. Use it for a service account.

To call PDC as a signed-in user, write your own provider that returns the user's access token and refreshes it as your app requires. The protocol is structural, so your class doesn't need to import or subclass anything from this package.

PDC applies the caller's permissions to every request. The same call can return different records for different tokens, and a record the caller may not view comes back as a 404, not a 403.

## Reading data

There are two ways to read a list.

**Iterate everything.** `get_changemakers`, `get_funders`, `get_proposals`, `get_initiatives`, and the other `get_*` list functions are generators that walk every page for you:

```python
from pdc_api_client.client import get_changemaker_proposals

for link in get_changemaker_proposals(session, changemaker_id=7):
    print(link.proposal_id)
```

**Fetch one page.** `get_bundle_page` returns a single page as a bundle, which is what a paginated UI needs. It takes the bundle type, a page number, an optional page size, and an optional search string:

```python
from pdc_api_client.client import get_bundle_page
from pdc_api_client.models import FunderBundle

page = get_bundle_page(session, FunderBundle, page=2, count_per_page=25, content="climate")
print(page.total, [funder.name for funder in page.entries])
```

Bundles for nested endpoints take path parameters, such as `get_bundle_page(session, FunderCollaborativeMemberBundle, path_params={"funder_collaborative_short_code": "acme"})`. Query parameters that `get_bundle_page` doesn't name go in `extra_params`.

## Writing data

The client covers the writes a proposal workflow needs: creating a proposal, adding a version with field values, linking a changemaker to it, and uploading files.

```python
from pdc_api_client.client import create_changemaker_proposal, create_changemaker_proposal_version
from pdc_api_client.models import NewProposalFieldValue, NewProposalVersion

proposal = create_changemaker_proposal(session, data={"opportunityId": 5, "externalId": "app-2026-001"})
version = create_changemaker_proposal_version(
    session,
    proposal_version=NewProposalVersion(
        proposal_id=proposal.id,
        source_id=3,
        application_form_id=12,
        field_values=[NewProposalFieldValue(application_form_field_id=88, position=1, value="Summer meals")],
    ),
)
```

A changemaker can also write its own profile values. `create_changemaker_source` creates a source the changemaker owns, `create_changemaker_field_value_batch` opens a batch under it, and `create_changemaker_field_value` adds one value to the batch. PDC ranks changemaker-sourced values above funder and data-provider values.

Uploading a file takes two steps. `register_file_upload` creates the file record and returns a presigned S3 POST, and `upload_file_to_s3_presigned_url` sends the bytes to it.

## Permission grants

PDC controls access with permission grants. Each grant gives a grantee (a user, a Keycloak organization, or every authenticated user) a set of verbs (such as `view` or `edit`) over a set of scopes, in the context of one entity such as a changemaker or a proposal. `pdc_api_client.permission_grants` models each context as its own class, so a grant parses into, say, `ChangemakerPermissionGrant` with a typed `changemaker_id`:

```python
from pdc_api_client.models import PermissionGrantEntityType, PermissionGrantGranteeType, PermissionGrantVerb
from pdc_api_client.permission_grants import ChangemakerPermissionGrant, create_permission_grant, list_permission_grants

grant = create_permission_grant(
    session,
    spec=ChangemakerPermissionGrant(
        changemaker_id=7,
        grantee_type=PermissionGrantGranteeType.USER_GROUP,
        grantee_keycloak_organization_id="1f0c6e2a-7d4b-4c55-9a51-0d8c2f0b6a11",
        verbs=[PermissionGrantVerb.VIEW],
        scope=[PermissionGrantEntityType.CHANGEMAKER, PermissionGrantEntityType.PROPOSAL],
    ),
)

page = list_permission_grants(session, changemaker=7, verb=PermissionGrantVerb.VIEW)
```

The models check that the grantee fields match `grantee_type` before anything is sent. Create, get, update, and delete functions exist for grants and for default permission grants. A default permission grant has no context entity; PDC copies it into a real grant on each new entity of its type as that entity is created.

## Errors

`APISession` raises a subclass of `pdc_api_client.PDCException` for every failed request. Each exception has `.code` (the HTTP status) and `.detail` (the parsed JSON body, or the raw text when the body isn't JSON).

| Status        | Exception                     |
| ------------- | ----------------------------- |
| 400           | `PDCBadRequestError`          |
| 401           | `PDCUnauthorizedError`        |
| 403           | `PDCForbiddenError`           |
| 404           | `PDCNotFoundError`            |
| 409           | `PDCConflictError`            |
| 422           | `PDCUnprocessableEntityError` |
| 5xx, timeout, or connection failure | `PDCServiceError` |
| Any other non-2xx | `PDCException`            |

A few lookups turn a 404 into an error named for the resource: `get_proposal` and `get_changemaker_proposal` raise `ProposalNotFoundError`, `get_changemaker` raises `ChangemakerNotFoundError`, `get_funder` raises `FunderNotFoundError`, `get_changemaker_field_value_batch` raises `ChangemakerFieldValueBatchNotFoundError`, and `get_application_form_by_name` raises `ApplicationFormNotFoundError`, a `PDCNotFoundError`, when no form has that name. `KeycloakClientCredentialsProvider` raises `TokenRequestError` when Keycloak rejects the grant.

## Models

Most models are generated from PDC's OpenAPI spec, which is pinned in `src/pdc_api_client/openapi.json`. Import them from `pdc_api_client.models`; `pdc_api_client._generated` is an implementation detail.

The models ignore fields they don't declare. When PDC adds a field to a response, parsing keeps working, and the new field appears once the models are regenerated.

The spec doesn't always match what PDC returns. Some fields it marks required are missing or null in real responses, and a few shapes don't generate usable models. `codegen/preprocess.py` patches each mismatch before generation, one function per problem. Each rule names the mismatch it patches, and should be deleted once PDC's spec matches its responses. We reported the first batch in [PhilanthropyDataCommons/service#2451](https://github.com/PhilanthropyDataCommons/service/issues/2451).

## What's not covered yet

The client covers most of the API but not all of it:

- **No client functions:** `/applicationFormFields`, `/sources`, `/tasks` (bulk uploads and base field copies), `/terminologySets`, and `/users`. Their models are generated, and `session.get`/`session.post` reach any endpoint directly.
- **Writes outside the proposal workflow:** creating funders, changemakers, opportunities, sources, and the like exists only as seeding helpers in `pdc_api_client.seeding`, which aren't meant for production data.
- **Async:** the client is synchronous and built on `requests`.

Issues and pull requests that fill these gaps are welcome.

## Testing your code

`pdc_api_client.testing` (extra: `testing`) registers mocked PDC responses with `responses`. It has payload builders that return valid response bodies, and `add_*_response` functions that register them for a base URL:

```python
import responses

from pdc_api_client import APISession, testing
from pdc_api_client.client import get_bundle_page
from pdc_api_client.models import ChangemakerBundle

BASE_URL = "https://pdc.test/"


class StaticToken:
    def get_token(self) -> str:
        return "test-token"

    def refresh_if_necessary(self) -> None:
        pass


@responses.activate
def test_lists_changemakers():
    testing.add_page_response(
        ChangemakerBundle,
        base_url=BASE_URL,
        payload=testing.bundle([testing.changemaker_payload(id=1, name="Acme")]),
    )
    session = APISession(base_url=BASE_URL, token_provider=StaticToken())

    page = get_bundle_page(session, ChangemakerBundle)

    assert page.entries[0].name == "Acme"
```

## Seeding a PDC stack

`pdc_api_client.seeding` (extra: `seeding`) creates realistic data on a PDC stack through the public PDC API and the Keycloak admin API. It is for local development and integration tests, not production:

- **`pdc_api_client.seeding.pdc_entities`:** `seed_*` functions for funders, collaboratives, changemakers, fiscal sponsorships, data providers, opportunities, application forms, proposals, initiatives, and field values. `seed_proposal_bundle` creates a full proposal and everything it depends on in one call.
- **`pdc_api_client.seeding.keycloak_admin`:** `KeycloakAdmin`, whose `ensure_*` methods create Keycloak organizations, users, memberships, and realm roles only if they don't already exist, so re-running a seed script is safe.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, tests, and regenerating the models.

## License

[AGPL-3.0](LICENSE). Maintained by [DrivenData](https://drivendata.org).
