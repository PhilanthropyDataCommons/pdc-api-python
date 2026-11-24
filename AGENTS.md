This file guides AI agents (Claude, Codex, and others) working in this repository.

# pdc-api-python

A framework-free Python client for the Philanthropy Data Commons (PDC) API. The distribution is `pdc-api`; the import name is `pdc_api`. `README.md` is the user-facing documentation and `CONTRIBUTING.md` the developer documentation; keep both accurate when you change behavior.

## Boundaries

- No framework dependency, and no reference to any particular consumer in code, comments, or tests. Configuration arrives as arguments (`base_url`, `timeout`, a `TokenProvider`), never from settings or the environment. The integration tests are the one place that reads environment variables.
- Optional features live in extras: `pdc_api.testing` needs `[testing]`, `pdc_api.seeding` needs `[seeding]`. The core imports neither.

## Models and codegen

- `src/pdc_api/_generated.py` is generated from `src/pdc_api/openapi.json` by `just codegen`. Never edit it by hand, and import models from `pdc_api.models`.
- Generated code owns field shapes. `models.py` owns client concerns: bundle `pdc_endpoint` and `default_page_size` ClassVars, aliases, and write-only request models. `permission_grants.py` models the grant union by hand.
- After `just update-api-spec`, record the spec's `info.version` and the download date in `CHANGELOG.md`; PDC changes the spec without bumping that version.
- When the spec disagrees with what PDC returns, add a rule to `codegen/preprocess.py` with a one-line comment naming the mismatch, then regenerate. Delete a rule once PDC fixes the cause. CI fails if `_generated.py` drifts from the spec.

## API conventions

- `session` is the first positional argument; every other argument is keyword-only. The exception is the bundle type in `get_bundle_page` and `pdc_api.testing.add_page_response`, which names the endpoint.
- Errors end in `Error`, except the base class `PDCException`. A lookup's not-found error subclasses `PDCNotFoundError`.

## Commands

- `just test [--python VERSION] [--lowest-direct] [--upgrade] [-- ARGS]` runs the unit tests, which mock all HTTP with `responses`. `just integration` takes the same options. Both run against the installed package in an isolated environment, with the versions in `uv.lock` unless `--lowest-direct` or `--upgrade` resolves them fresh. Arguments after `--` go to pytest.
- `just pdc up` starts PDC's CI stack in Docker; `just integration` runs the live suite against it.
- `just typecheck` runs mypy (with the pydantic plugin) over `src` and both test suites, mypy in strict mode over `src`, then pyrefly and ty over `src` and both test suites, and fails at the end if any of them failed. `just typecheck-mypy`, `just typecheck-pyrefly`, and `just typecheck-ty` run one checker each. All take `--python` and `--lowest-direct`, which work as they do for `just test`.
- `just zizmor` audits the GitHub Actions workflows; run it after changing anything in `.github/`. It runs offline audits only unless `GH_TOKEN` is set. Arguments go to zizmor.
- Releases go through the Release workflow, which creates the tag; see "Releasing" in `CONTRIBUTING.md`. New changelog entries go under `## Unreleased`.
- Verify with `just check` (lint, type checks, and both suites). The unit tests can't catch a change in PDC's behavior; if the stack isn't available, run `just lint`, `just typecheck`, and `just test` and say that integration verification is pending.

## Standards

- Readability, simplicity, and elegance, in that order.
- Write the test before the code. Assert transformations and branch behavior, not that a mock returned what it was given.
- When behavior varies by enum member or union variant, write the expected outcome for every member as a literal table in the test, parametrize over that table, and assert the table covers the whole enum or union. A value that codegen adds then fails a test by name until someone records how it behaves, and a wrong entry in the code's own lookup table fails too, because the test doesn't read it.
- Every client function gets an integration test against PDC as well as unit tests, unless PDC's CI stack can't support it.
- Tests live in `Test<Subject>` classes named for the function or class under test, with methods named `test_<behavior>` in the present tense, such as `TestGetProposal.test_raises_proposal_not_found_on_404`. Integration tests that cover a workflow across several functions may group by area instead, such as `TestProposals`.
- No docstrings, and comments only for a non-obvious why such as a PDC quirk, in one line.
- Lower bounds only in `pyproject.toml`. `uv.lock` pins the versions that development and CI use. CI also tests the lowest allowed versions on the oldest supported Python, and a weekly run tests the newest versions released at least a week ago, so raise a bound when you use something newer, and fix breakage from new releases rather than pinning.
