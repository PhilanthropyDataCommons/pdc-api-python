# Contributing

We use [uv](https://docs.astral.sh/uv/) and [just](https://just.systems):

```bash
uv sync
just test         # unit tests, no network
just typecheck    # mypy, pyrefly, and ty
just zizmor       # audit the GitHub Actions workflows
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

`just typecheck` takes `--python` and `--lowest-direct` too. CI type checks Python 3.12 with the lowest versions and Python 3.14 with `uv.lock`.

`uv.lock` pins the versions used for development and CI. Update it with `uv lock --upgrade`. CI also runs both suites weekly with `--upgrade`, and opens an issue when that run or a push to main fails.

`just pdc up` downloads PDC's [`compose-ci.yml`](https://github.com/PhilanthropyDataCommons/service/blob/main/compose-ci.yml) and Keycloak realm from the service repo's main branch and starts the stack: the PDC API, Keycloak, Postgres, and S3. The integration tests reach Keycloak at `pdc-auth`, so add this line to `/etc/hosts`:

```text
127.0.0.1 pdc-api pdc-auth pdc-s3
```

The integration tests read their settings from environment variables (`PDC_API_URL`, `KEYCLOAK_SERVER_URL`, and others in `integration_tests/conftest.py`), with defaults that match the CI stack.

The unit tests mock every HTTP call, so they can't catch a change in PDC's behavior. The integration tests can, and CI runs both on every pull request.

Both suites print a coverage report. CI reports each suite's coverage separately in the run summary, with unit coverage combined across the Python versions it tests. Each run uploads three artifacts:

- `coverage-html`: an HTML report for each suite.
- `coverage-json`: `unit.json` and `integration.json`, from `coverage json`.
- `coverage-data`: the raw coverage data from each test job, one directory per job.

```bash
gh run download <run-id> -n coverage-json
```

## Updating to a new PDC spec

```bash
just update-api-spec  # download the current spec into src/pdc_api/openapi.json
just codegen          # regenerate src/pdc_api/_generated.py
just check
```

Generation is deterministic, and CI fails if `_generated.py` doesn't match the pinned spec. When a regenerated model breaks against real PDC data, add or change a rule in `codegen/preprocess.py`. Don't edit `_generated.py` by hand. Delete a rule once PDC fixes the problem it patches.

## Releasing

1. Open a pull request that bumps `version` in `pyproject.toml`, runs `uv lock`, and renames the changelog's `## Unreleased` heading to `## X.Y.Z (YYYY-MM-DD)`. Merge it.
2. On the [Release workflow](https://github.com/PhilanthropyDataCommons/pdc-api-python/actions/workflows/release.yml) page, click **Run workflow**, leave the branch on `main`, enter the tag `vX.Y.Z`, and run it.

The workflow checks that the tag matches the package version, doesn't exist yet, and has a dated changelog entry. It then builds and inspects the package, uploads it to Test PyPI and then PyPI, and creates the tag and GitHub release on the commit it ran on, with the changelog entry as the notes. Don't create the tag by hand.

Check **Dry run** to upload to Test PyPI only and skip the PyPI upload and the GitHub release. A dry run can run from any branch.

PyPI and Test PyPI publish through [trusted publishing](https://docs.pypi.org/trusted-publishers/), from the `release.yml` workflow in the `release` environment.

Issues and pull requests are welcome.
