This file guides AI agents (Claude, Codex, and others) working in this repository.

# pdc-python-client

A framework-free Python client for the Philanthropy Data Commons (PDC) API. The distribution is `pdc-python-client`; the import name is `pdc_api_client`. `README.md` is the user-facing documentation and `CONTRIBUTING.md` the developer documentation; keep both accurate when you change behavior.

## Boundaries

- No framework dependency, and no reference to any particular consumer in code, comments, or tests. Configuration arrives as arguments (`base_url`, `timeout`, a `TokenProvider`), never from settings or the environment. The integration tests are the one place that reads environment variables.
- Optional features live in extras: `pdc_api_client.testing` needs `[testing]`, `pdc_api_client.seeding` needs `[seeding]`. The core imports neither.

## Models and codegen

- `src/pdc_api_client/_generated.py` is generated from `src/pdc_api_client/openapi.json` by `just codegen`. Never edit it by hand, and import models from `pdc_api_client.models`.
- Generated code owns field shapes. `models.py` owns client concerns: bundle `pdc_endpoint` and `default_page_size` ClassVars, aliases, and write-only request models. `permission_grants.py` models the grant union by hand.
- After `just update-api-spec`, record the spec's `info.version` and the download date in `CHANGELOG.md`; PDC changes the spec without bumping that version.
- When the spec disagrees with what PDC returns, add a rule to `codegen/preprocess.py` with a one-line docstring naming the mismatch, then regenerate. Delete a rule once PDC fixes the cause. CI fails if `_generated.py` drifts from the spec.

## API conventions

- `session` is the first positional argument; every other argument is keyword-only. The exception is the bundle type in `get_bundle_page` and `pdc_api_client.testing.add_page_response`, which names the endpoint.
- Domain errors end in `Error`.

## Commands

- `just test [--python VERSION] [--lowest-direct] [--upgrade] [-- ARGS]` runs the unit tests, which mock all HTTP with `responses`. `just integration` takes the same options. Both run against the installed package in an isolated environment, with the versions in `uv.lock` unless `--lowest-direct` or `--upgrade` resolves them fresh. Arguments after `--` go to pytest.
- `just pdc up` starts PDC's CI stack in Docker; `just integration` runs the live suite against it.
- Verify with `just check` (lint plus both suites). The unit tests can't catch a change in PDC's behavior; if the stack isn't available, run `just test` and `just lint` and say that integration verification is pending.

## Standards

- Readability, simplicity, and elegance, in that order.
- Write the test before the code. Assert transformations and branch behavior, not that a mock returned what it was given.
- Every client function gets an integration test against PDC as well as unit tests, unless PDC's CI stack can't support it.
- No docstrings, and comments only for a non-obvious why such as a PDC quirk, in one line.
- Lower bounds only in `pyproject.toml`. `uv.lock` pins the versions that development and CI use. CI also tests the lowest allowed versions on the oldest supported Python, and a weekly run tests the newest versions, so raise a bound when you use something newer, and fix breakage from new releases rather than pinning.
