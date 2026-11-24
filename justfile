# Keep in sync with just-version in .github/workflows/ci.yml
set minimum-version := '1.55.0'

mod pdc 'just/pdc.just'

set positional-arguments

python := env("PYTHON", shell("cat .python-version"))
lowest_direct := env("LOWEST_DIRECT", "false")
upgrade := env("UPGRADE", "false")
isolated_run := "uv run --python=" + python + (if lowest_direct == "true" { " --resolution=lowest-direct" } else { "" }) + " --isolated --no-dev"
pytest := isolated_run + (if upgrade == "true" { " --upgrade" } else { "" }) + " --no-editable --group tests --reinstall -- python -I -m pytest"
typecheck_run := isolated_run + " --group tests --group typecheck --"

_default:
    @just --list --unsorted

# Lint and check formatting
[group('dev')]
lint:
    uv run ruff check .
    uv run ruff format . --check

# Format and autofix lint issues
[group('dev')]
format:
    uv run ruff format .
    uv run ruff check . --fix

# Audit GitHub Actions workflows with zizmor (passes through args)
[group('dev')]
zizmor *args:
    uvx --exclude-newer "7 days" zizmor .github/ "$@"

# Run all three type checkers, failing at the end if any failed
[group('dev')]
typecheck:
    #!/usr/bin/env bash
    status=0
    for checker in mypy pyrefly ty; do
        {{just_executable()}} typecheck-$checker || status=1
    done
    exit $status

# Type check the package and tests with mypy, then the package in strict mode
[group('dev')]
typecheck-mypy:
    #!/usr/bin/env bash
    status=0
    {{typecheck_run}} mypy --python-version={{python}} || status=1
    {{typecheck_run}} mypy --python-version={{python}} --strict src || status=1
    exit $status

# Type check the package and tests with pyrefly
[group('dev')]
typecheck-pyrefly *args:
    {{typecheck_run}} pyrefly check --python-version={{python}} "$@"

# Type check the package and tests with ty
[group('dev')]
typecheck-ty *args:
    {{typecheck_run}} ty check --python-version={{python}} "$@"

# Run the unit tests against the installed package
[group('test')]
test *args: _preview-upgrade
    {{pytest}} "$@"

# Run the integration tests against the installed package and a live PDC stack (run `just pdc up` first)
[group('test')]
integration *args: _preview-upgrade
    {{pytest}} integration_tests/ "$@"

_preview-upgrade:
    @if [ "{{upgrade}}" = true ]; then uv lock --upgrade --dry-run; fi

# Run lint, type checks, unit tests, and integration tests (run `just pdc up` first)
[group('test')]
check: lint typecheck test integration

# Download the current PDC OpenAPI spec
[group('codegen')]
update-api-spec:
    curl -fsSL https://api.philanthropydatacommons.org/openapi/api.json -o src/pdc_api/openapi.json
    uv run python -c "import json; json.load(open('src/pdc_api/openapi.json'))"

# Regenerate src/pdc_api/_generated.py from src/pdc_api/openapi.json
[group('codegen')]
codegen:
    uv run python codegen/preprocess.py src/pdc_api/openapi.json codegen/openapi.preprocessed.json
    uv run datamodel-codegen \
      --input codegen/openapi.preprocessed.json --input-file-type openapi \
      --output src/pdc_api/_generated.py \
      --output-model-type pydantic_v2.BaseModel \
      --base-class pdc_api._base.BaseSchema \
      --snake-case-field --use-annotated --use-standard-collections --use-union-operator \
      --collapse-root-models --capitalise-enum-members --target-python-version 3.12 --disable-timestamp \
      --formatters ruff-format ruff-check
    uv run python codegen/postprocess.py src/pdc_api/_generated.py
    uv run ruff format src/pdc_api/_generated.py
