# Contributing

We use [uv](https://docs.astral.sh/uv/) and [just](https://just.systems):

```bash
uv sync
just test         # unit tests, no network
just typecheck    # mypy, pyrefly, and ty
just pdc up       # start PDC's CI stack in Docker
just integration  # integration tests against that stack
just check        # lint, type checks, unit tests, and integration tests
```

`just test` and `just integration` install the package into an isolated environment and run the tests against it, using the Python version in `.python-version` and the versions in `uv.lock`. Both take the same options, and pass arguments after `--` to pytest:

- `--python VERSION` uses another Python.
- `--lowest-direct` uses the lowest versions of direct dependencies that `pyproject.toml` allows.
- `--upgrade` uses the newest versions released at least a week ago (`exclude-newer` in `pyproject.toml`) and prints how they differ from `uv.lock`, without changing it.

```bash
just test --python 3.12 --lowest-direct -- -k token
```

`uv.lock` pins the versions used for development and CI. Update it with `uv lock --upgrade`. CI also runs both suites weekly with `--upgrade`, and opens an issue when that run fails.

`just pdc up` downloads PDC's [`compose-ci.yml`](https://github.com/PhilanthropyDataCommons/service/blob/main/compose-ci.yml) and Keycloak realm from the service repo's main branch and starts the stack: the PDC API, Keycloak, Postgres, and S3. The integration tests reach Keycloak at `pdc-auth`, so add this line to `/etc/hosts`:

```text
127.0.0.1 pdc-api pdc-auth pdc-s3
```

The integration tests read their settings from environment variables (`PDC_API_URL`, `KEYCLOAK_SERVER_URL`, and others in `integration_tests/conftest.py`), with defaults that match the CI stack.

The unit tests mock every HTTP call, so they can't catch a change in PDC's behavior. The integration tests can, and CI runs both on every pull request.

## Updating to a new PDC spec

```bash
just update-api-spec  # download the current spec into src/pdc_api_client/openapi.json
just codegen          # regenerate src/pdc_api_client/_generated.py
just check
```

Generation is deterministic, and CI fails if `_generated.py` doesn't match the pinned spec. When a regenerated model breaks against real PDC data, add or change a rule in `codegen/preprocess.py`. Don't edit `_generated.py` by hand. Delete a rule once PDC fixes the problem it patches.

Issues and pull requests are welcome.
